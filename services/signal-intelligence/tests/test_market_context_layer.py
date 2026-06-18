from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from zulu_contracts.domain import OptionType
from zulu_signal_intelligence.constraints import MarketDataQualityError
from zulu_signal_intelligence.context_service import (
    MarketContextService,
    MarketContextUnavailableError,
)
from zulu_signal_intelligence.features import generate_canonical_feature_vector
from zulu_signal_intelligence.fixture_provider import FixtureMarketDataProvider
from zulu_signal_intelligence.normalizers import (
    conservative_catalyst_summary,
    is_safe_headline_url,
    normalize_headlines,
    normalize_option_contract,
    normalize_stock_bars,
    normalize_stock_quote,
)
from zulu_signal_intelligence.provider_models import (
    ProviderCapabilities,
    ProviderCapability,
    ProviderHealth,
    ProviderHealthState,
    ProviderProvenance,
    RawHeadline,
    RawOptionContract,
    RawStockBar,
    RawStockQuote,
)
from zulu_signal_intelligence.providers import (
    EnvironmentGatedProviderClient,
    ProviderConfigurationError,
)
from zulu_signal_intelligence.resilience import (
    CircuitBreaker,
    ProviderCircuitOpenError,
    ProviderExecutor,
    ProviderRateLimitError,
    ProviderTimeoutError,
    RetryPolicy,
)
from zulu_signal_intelligence.weather import MarketWeatherService

NOW = datetime(2026, 6, 18, 14, 30, tzinfo=UTC)
TENANT_ID = "tenant_demo"
TICKER = "MSFT"


def test_fixture_provider_exposes_health_and_capabilities() -> None:
    provider = FixtureMarketDataProvider(now=NOW)

    assert provider.health().state == "healthy"
    capabilities = provider.capabilities()
    assert capabilities.supports(ProviderCapability.STOCK_QUOTES)
    assert capabilities.supports(ProviderCapability.OPTIONS_GREEKS)


def test_context_service_builds_validated_market_context_with_fixture_provider() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    bundle = MarketContextService(provider).build_context(
        tenant_id=TENANT_ID,
        ticker=TICKER,
        option_symbol="MSFT270117C00100000",
        now=NOW,
    )

    assert bundle.market_data.ticker == TICKER
    assert bundle.option_contract is not None
    assert bundle.market_weather.regime in {"risk_on", "balanced", "risk_off"}
    assert bundle.feature_vector.content_hash
    assert bundle.provider_capabilities.supports(ProviderCapability.HEADLINES)
    assert {event.code for event in bundle.data_quality} >= {
        "provider_preflight_passed",
        "market_context_normalized",
    }


def test_headlines_are_deduplicated_and_incomplete_provider_metadata_is_not_verified() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    incomplete = RawHeadline(
        provider_headline_id="missing-metadata",
        title="MSFT incomplete provider metadata",
        source_name=None,
        url="https://fixture.local/news/incomplete",
        published_at=None,
        tickers=[TICKER],
        provenance=provider._provenance("missing-metadata"),
    )

    headlines = normalize_headlines(
        [*provider.get_headlines([TICKER]), incomplete],
        tenant_id=TENANT_ID,
        now=NOW,
    )

    assert len(headlines) == 1
    assert headlines[0].ticker == TICKER


def test_stale_stock_quote_is_rejected() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    stale_quote = provider.get_stock_quote(TICKER).model_copy(
        update={"observed_at": NOW - timedelta(minutes=10)}
    )

    with pytest.raises(MarketDataQualityError, match="stale"):
        normalize_stock_quote(stale_quote, tenant_id=TENANT_ID, now=NOW)


def test_stale_stock_bars_are_rejected_before_feature_generation() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    stale_bars = [
        bar.model_copy(
            update={
                "started_at": bar.started_at - timedelta(minutes=10),
                "ended_at": bar.ended_at - timedelta(minutes=10),
            }
        )
        for bar in provider.get_stock_bars(TICKER)
    ]

    with pytest.raises(MarketDataQualityError, match="stock bars"):
        normalize_stock_bars(stale_bars, now=NOW)


def test_context_service_rejects_stale_bars_before_signal_context() -> None:
    class StaleBarsProvider(FixtureMarketDataProvider):
        def get_stock_bars(self, ticker: str) -> list[RawStockBar]:
            return [
                bar.model_copy(
                    update={
                        "started_at": bar.started_at - timedelta(minutes=10),
                        "ended_at": bar.ended_at - timedelta(minutes=10),
                    }
                )
                for bar in super().get_stock_bars(ticker)
            ]

    with pytest.raises(MarketDataQualityError, match="stock bars"):
        MarketContextService(StaleBarsProvider(now=NOW)).build_context(
            tenant_id=TENANT_ID,
            ticker=TICKER,
            now=NOW,
        )


def test_stock_bars_are_sorted_and_duplicates_are_rejected() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    bars = provider.get_stock_bars(TICKER)

    ordered = normalize_stock_bars(list(reversed(bars)), now=NOW)

    assert ordered[0].ended_at > ordered[1].ended_at
    with pytest.raises(MarketDataQualityError, match="duplicate"):
        normalize_stock_bars([bars[0], bars[0]], now=NOW)


def test_missing_option_open_interest_requires_explicit_rule() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    raw_option = provider.get_option_contract("MSFT270117C00100000").model_copy(
        update={"open_interest": None}
    )

    with pytest.raises(MarketDataQualityError, match="open interest"):
        normalize_option_contract(raw_option, tenant_id=TENANT_ID, now=NOW)


def test_option_contract_symbol_must_match_provider_metadata() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    mismatched = provider.get_option_contract("MSFT270117C00100000").model_copy(
        update={"underlying_ticker": "AAPL"}
    )

    with pytest.raises(MarketDataQualityError, match="underlying"):
        normalize_option_contract(mismatched, tenant_id=TENANT_ID, now=NOW)


def test_missing_option_greeks_are_marked_unavailable_not_zeroed() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    raw_option = provider.get_option_contract("MSFT270117C00100000").model_copy(
        update={
            "delta": None,
            "gamma": None,
            "theta": None,
            "vega": None,
            "implied_volatility": None,
        }
    )
    market_data = normalize_stock_quote(
        provider.get_stock_quote(TICKER), tenant_id=TENANT_ID, now=NOW
    )
    option_contract = normalize_option_contract(raw_option, tenant_id=TENANT_ID, now=NOW)
    headlines = normalize_headlines(provider.get_headlines([TICKER]), tenant_id=TENANT_ID, now=NOW)
    broad_context = provider.get_broad_market_context()
    weather = MarketWeatherService().classify(
        tenant_id=TENANT_ID,
        broad_context=broad_context,
        calendar=provider.get_market_calendar(),
        headlines=headlines,
        now=NOW,
    )

    vector = generate_canonical_feature_vector(
        tenant_id=TENANT_ID,
        ticker=TICKER,
        market_data=market_data,
        bars=provider.get_stock_bars(TICKER),
        broad_context=broad_context,
        market_weather=weather.snapshot,
        headline_sentiment_score=Decimal("0.25"),
        headline_count=len(headlines),
        generated_at=NOW,
        option_contract=option_contract,
    )

    assert vector.feature_values["canonical_v1.options.greeks_available"] == Decimal("0.000000")
    assert vector.feature_values["canonical_v1.options.implied_volatility_available"] == Decimal(
        "0.000000"
    )
    assert "canonical_v1.options.delta" not in vector.feature_values
    assert "canonical_v1.options.implied_volatility" not in vector.feature_values


def test_provider_health_and_capability_preflight_fails_closed() -> None:
    class UnavailableProvider(FixtureMarketDataProvider):
        def health(self) -> ProviderHealth:
            return ProviderHealth(
                provider_name=self.provider_name,
                state=ProviderHealthState.UNAVAILABLE,
                checked_at=NOW,
                detail="unit outage",
            )

    with pytest.raises(MarketContextUnavailableError, match="provider health"):
        MarketContextService(UnavailableProvider(now=NOW)).build_context(
            tenant_id=TENANT_ID,
            ticker=TICKER,
            now=NOW,
        )

    class MissingBarsProvider(FixtureMarketDataProvider):
        def capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(
                provider_name=self.provider_name,
                capabilities=frozenset({ProviderCapability.STOCK_QUOTES}),
            )

    with pytest.raises(MarketContextUnavailableError, match="missing required capabilities"):
        MarketContextService(MissingBarsProvider(now=NOW)).build_context(
            tenant_id=TENANT_ID,
            ticker=TICKER,
            now=NOW,
        )


def test_provider_outage_is_explicit_degraded_failure_not_empty_success() -> None:
    class OutageProvider(FixtureMarketDataProvider):
        def get_stock_quote(self, ticker: str) -> RawStockQuote:
            raise RuntimeError("quote path down")

    with pytest.raises(MarketContextUnavailableError, match="stock_quote unavailable"):
        MarketContextService(OutageProvider(now=NOW)).build_context(
            tenant_id=TENANT_ID,
            ticker=TICKER,
            now=NOW,
        )


def test_provider_response_cache_uses_tenant_provider_operation_and_ttl() -> None:
    class CountingProvider(FixtureMarketDataProvider):
        quote_calls: int = 0

        def get_stock_quote(self, ticker: str) -> RawStockQuote:
            self.quote_calls += 1
            return super().get_stock_quote(ticker)

    provider = CountingProvider(now=NOW)
    service = MarketContextService(provider)

    service.build_context(tenant_id=TENANT_ID, ticker=TICKER, now=NOW)
    service.build_context(tenant_id=TENANT_ID, ticker=TICKER, now=NOW + timedelta(seconds=10))
    service.build_context(tenant_id=TENANT_ID, ticker=TICKER, now=NOW + timedelta(seconds=20))

    assert provider.quote_calls == 2


def test_feature_vector_hash_is_stable_for_same_inputs() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    service = MarketContextService(provider)

    first = service.build_context(tenant_id=TENANT_ID, ticker=TICKER, now=NOW).feature_vector
    second = service.build_context(tenant_id=TENANT_ID, ticker=TICKER, now=NOW).feature_vector

    assert first.feature_values == second.feature_values
    assert first.content_hash == second.content_hash
    assert "canonical_v1.vwap.last_vs_vwap" in first.feature_values
    assert "canonical_v1.weather.risk_on_score" in first.feature_values


def test_market_weather_service_exposes_transparent_components() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    headlines = normalize_headlines(provider.get_headlines([TICKER]), tenant_id=TENANT_ID, now=NOW)

    weather = MarketWeatherService().classify(
        tenant_id=TENANT_ID,
        broad_context=provider.get_broad_market_context(),
        calendar=provider.get_market_calendar(),
        headlines=headlines,
        now=NOW,
    )

    component_names = {component.name for component in weather.components}
    assert {
        "index_trend",
        "volatility_regime",
        "breadth_participation",
        "sector_alignment",
        "liquidity_quality",
        "headline_pressure",
        "session_timing",
        "risk_posture",
    } <= component_names


def test_provider_executor_retries_rate_limits_then_succeeds() -> None:
    attempts = 0

    def flaky_call() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ProviderRateLimitError("rate limited")
        return "ok"

    executor = ProviderExecutor(retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0))

    assert executor.call("fixture-provider", flaky_call) == "ok"
    assert attempts == 3


def test_provider_executor_opens_circuit_after_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=1)
    executor = ProviderExecutor(
        retry_policy=RetryPolicy(max_attempts=1, base_delay_seconds=0),
        circuit_breaker=breaker,
    )

    with pytest.raises(ProviderRateLimitError):
        executor.call(
            "fixture-provider",
            lambda: (_ for _ in ()).throw(ProviderRateLimitError("rate limited")),
        )
    with pytest.raises(ProviderCircuitOpenError):
        executor.call("fixture-provider", lambda: "ok")


def test_provider_executor_times_out_slow_operations() -> None:
    executor = ProviderExecutor(
        retry_policy=RetryPolicy(max_attempts=1, base_delay_seconds=0, timeout_seconds=0)
    )

    with pytest.raises(ProviderTimeoutError):
        executor.call("fixture-provider", lambda: "slow")


def test_environment_gated_provider_client_requires_enabled_config_and_credentials() -> None:
    disabled = EnvironmentGatedProviderClient(provider_name="vendor", enabled=False)
    with pytest.raises(ProviderConfigurationError, match="disabled"):
        disabled.ensure_enabled()

    missing_secret = EnvironmentGatedProviderClient(provider_name="vendor", enabled=True)
    with pytest.raises(ProviderConfigurationError, match="credential"):
        missing_secret.ensure_enabled()

    enabled = EnvironmentGatedProviderClient(
        provider_name="vendor", enabled=True, api_key="present"
    )
    enabled.ensure_enabled()


def test_raw_option_contract_requires_valid_expiration() -> None:
    provenance = ProviderProvenance(
        provider_name="unit",
        provider_mode="fixture",
        provider_record_id="bad-option",
        retrieved_at=NOW,
    )

    with pytest.raises(ValueError, match="expiration"):
        RawOptionContract(
            underlying_ticker=TICKER,
            option_symbol="MSFT270117C00100000",
            option_type=OptionType.CALL,
            strike=Decimal("100"),
            expiration_date=NOW - timedelta(days=1),
            multiplier=100,
            bid=Decimal("4.10"),
            ask=Decimal("4.25"),
            observed_at=NOW,
            provenance=provenance,
        )


def test_headline_url_safety_and_summary_state_are_explicit() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    unsafe = RawHeadline(
        provider_headline_id="unsafe",
        title="MSFT unsafe provider URL",
        source_name="Fixture Newswire",
        url="http://127.0.0.1/internal",
        published_at=NOW - timedelta(hours=1),
        tickers=[TICKER],
        summary=None,
        provenance=provider._provenance("unsafe"),
    )

    headlines = normalize_headlines([unsafe], tenant_id=TENANT_ID, now=NOW)

    assert headlines == []
    assert is_safe_headline_url("https://fixture.local/news/steady-demand")
    assert not is_safe_headline_url("file:///tmp/news")
    assert "summary_unavailable" in conservative_catalyst_summary(unsafe)
