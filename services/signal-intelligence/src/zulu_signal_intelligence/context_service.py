from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TypeVar, cast

from zulu_contracts import (
    CanonicalFeatureVectorV1,
    HeadlineEvent,
    MarketDataSnapshot,
    MarketWeatherSnapshot,
    OptionContractSnapshot,
)

from zulu_signal_intelligence.cache import ProviderCacheKey, ProviderResponseCache
from zulu_signal_intelligence.features import generate_canonical_feature_vector
from zulu_signal_intelligence.normalizers import (
    normalize_headlines,
    normalize_option_contract,
    normalize_stock_bars,
    normalize_stock_quote,
)
from zulu_signal_intelligence.provider_models import (
    DataQualityMetadata,
    DataQualityStatus,
    ProviderCapabilities,
    ProviderCapability,
    ProviderHealth,
    ProviderHealthState,
)
from zulu_signal_intelligence.providers import MarketContextProviderSuite
from zulu_signal_intelligence.resilience import ProviderExecutor
from zulu_signal_intelligence.weather import MarketWeatherService, WeatherClassification

T = TypeVar("T")


@dataclass(frozen=True)
class MarketContextBundle:
    provider_health: ProviderHealth
    provider_capabilities: ProviderCapabilities
    data_quality: tuple[DataQualityMetadata, ...]
    market_data: MarketDataSnapshot
    option_contract: OptionContractSnapshot | None
    headlines: tuple[HeadlineEvent, ...]
    market_weather: MarketWeatherSnapshot
    feature_vector: CanonicalFeatureVectorV1
    weather: WeatherClassification


class MarketContextUnavailableError(RuntimeError):
    def __init__(
        self,
        *,
        tenant_id: str,
        provider_name: str,
        reason: str,
        operation: str | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.provider_name = provider_name
        self.operation = operation
        self.reason = reason
        detail = f"{provider_name} market context unavailable: {reason}"
        if operation is not None:
            detail = f"{provider_name} {operation} unavailable: {reason}"
        super().__init__(detail)


class MarketContextService:
    def __init__(
        self,
        provider: MarketContextProviderSuite,
        *,
        executor: ProviderExecutor | None = None,
        weather_service: MarketWeatherService | None = None,
        cache: ProviderResponseCache | None = None,
    ) -> None:
        self.provider = provider
        self.executor = executor or ProviderExecutor()
        self.weather_service = weather_service or MarketWeatherService()
        self.cache = cache or ProviderResponseCache()

    def build_context(
        self,
        *,
        tenant_id: str,
        ticker: str,
        now: datetime,
        option_symbol: str | None = None,
    ) -> MarketContextBundle:
        provider_health = self.provider.health()
        provider_capabilities = self.provider.capabilities()
        self._require_provider_ready(
            tenant_id=tenant_id,
            health=provider_health,
            capabilities=provider_capabilities,
            option_symbol=option_symbol,
        )
        quality_events = [
            _quality_event(
                status=DataQualityStatus.PASS,
                code="provider_preflight_passed",
                detail="provider health and required capabilities passed preflight",
                source=self.provider.provider_name,
                observed_at=provider_health.checked_at,
            )
        ]

        stock_quote = self._provider_call(
            tenant_id=tenant_id,
            operation_name="stock_quote",
            instrument=ticker,
            now=now,
            operation=self.provider.get_stock_quote,
            ticker=ticker,
        )
        stock_bars = self._provider_call(
            tenant_id=tenant_id,
            operation_name="stock_bars",
            instrument=ticker,
            now=now,
            operation=self.provider.get_stock_bars,
            ticker=ticker,
        )
        raw_headlines = self._provider_call(
            tenant_id=tenant_id,
            operation_name="headlines",
            instrument=ticker,
            now=now,
            operation=self.provider.get_headlines,
            tickers=[ticker],
        )
        calendar = self._provider_call(
            tenant_id=tenant_id,
            operation_name="market_calendar",
            instrument="market",
            now=now,
            operation=self.provider.get_market_calendar,
        )
        broad_context = self._provider_call(
            tenant_id=tenant_id,
            operation_name="broad_market_context",
            instrument="market",
            now=now,
            operation=self.provider.get_broad_market_context,
        )

        market_data = normalize_stock_quote(stock_quote, tenant_id=tenant_id, now=now)
        validated_bars = normalize_stock_bars(list(stock_bars), now=now)
        headlines = normalize_headlines(list(raw_headlines), tenant_id=tenant_id, now=now)
        weather = self.weather_service.classify(
            tenant_id=tenant_id,
            broad_context=broad_context,
            calendar=calendar,
            headlines=headlines,
            now=now,
        )
        option_contract = None
        if option_symbol is not None:
            raw_option = self._provider_call(
                tenant_id=tenant_id,
                operation_name="option_contract",
                instrument=option_symbol,
                now=now,
                operation=self.provider.get_option_contract,
                option_symbol=option_symbol,
            )
            option_contract = normalize_option_contract(raw_option, tenant_id=tenant_id, now=now)

        headline_sentiment = Decimal("0")
        if headlines:
            headline_sentiment = sum(
                (headline.sentiment_score for headline in headlines), Decimal("0")
            ) / Decimal(len(headlines))
        feature_vector = generate_canonical_feature_vector(
            tenant_id=tenant_id,
            ticker=ticker,
            market_data=market_data,
            bars=validated_bars,
            broad_context=broad_context,
            market_weather=weather.snapshot,
            headline_sentiment_score=headline_sentiment,
            headline_count=len(headlines),
            generated_at=now,
            option_contract=option_contract,
        )
        return MarketContextBundle(
            provider_health=provider_health,
            provider_capabilities=provider_capabilities,
            data_quality=tuple(
                [
                    *quality_events,
                    _quality_event(
                        status=DataQualityStatus.PASS,
                        code="market_context_normalized",
                        detail=(
                            "quotes, bars, headlines, market weather, and option data "
                            "passed validation"
                        ),
                        source=self.provider.provider_name,
                        observed_at=now,
                    ),
                ]
            ),
            market_data=market_data,
            option_contract=option_contract,
            headlines=tuple(headlines),
            market_weather=weather.snapshot,
            feature_vector=feature_vector,
            weather=weather,
        )

    def _require_provider_ready(
        self,
        *,
        tenant_id: str,
        health: ProviderHealth,
        capabilities: ProviderCapabilities,
        option_symbol: str | None,
    ) -> None:
        if health.state != ProviderHealthState.HEALTHY:
            raise MarketContextUnavailableError(
                tenant_id=tenant_id,
                provider_name=health.provider_name,
                reason=f"provider health is {health.state.value}: {health.detail}",
            )
        required = {
            ProviderCapability.STOCK_QUOTES,
            ProviderCapability.STOCK_BARS,
            ProviderCapability.HEADLINES,
            ProviderCapability.MARKET_CALENDAR,
            ProviderCapability.INDEX_CONTEXT,
            ProviderCapability.SECTOR_CONTEXT,
            ProviderCapability.VOLATILITY_CONTEXT,
        }
        if option_symbol is not None:
            required |= {
                ProviderCapability.OPTIONS_QUOTES,
                ProviderCapability.OPTIONS_OPEN_INTEREST,
            }
        missing = sorted(
            capability.value for capability in required if not capabilities.supports(capability)
        )
        if missing:
            raise MarketContextUnavailableError(
                tenant_id=tenant_id,
                provider_name=capabilities.provider_name,
                reason=f"provider missing required capabilities: {', '.join(missing)}",
            )

    def _provider_call(
        self,
        *,
        tenant_id: str,
        operation_name: str,
        instrument: str,
        now: datetime,
        operation: Callable[..., T],
        **kwargs: object,
    ) -> T:
        cache_key = ProviderCacheKey(
            tenant_id=tenant_id,
            provider_name=self.provider.provider_name,
            operation=operation_name,
            instrument=instrument,
        )
        cached = self.cache.get(cache_key, now=now)
        if cached is not None:
            return cast(T, cached)
        try:
            result = self.executor.call(self.provider.provider_name, operation, **kwargs)
        except Exception as exc:
            raise MarketContextUnavailableError(
                tenant_id=tenant_id,
                provider_name=self.provider.provider_name,
                operation=operation_name,
                reason=str(exc),
            ) from exc
        self.cache.set(cache_key, result, now=now)
        return result


def _quality_event(
    *,
    status: DataQualityStatus,
    code: str,
    detail: str,
    source: str,
    observed_at: datetime,
) -> DataQualityMetadata:
    return DataQualityMetadata(
        status=status,
        code=code,
        detail=detail,
        source=source,
        observed_at=observed_at,
    )
