from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from hashlib import sha256

from zulu_contracts import (
    CanonicalFeatureVectorV1,
    MarketDataSnapshot,
    MarketWeatherSnapshot,
    OptionContractSnapshot,
)

from zulu_signal_intelligence.constraints import MarketDataQualityError, require_observed_count
from zulu_signal_intelligence.provider_models import RawBroadMarketContext, RawStockBar

FEATURE_SCHEMA_VERSION = "canonical_features_v1"


def generate_canonical_feature_vector(
    *,
    tenant_id: str,
    ticker: str,
    market_data: MarketDataSnapshot,
    bars: Sequence[RawStockBar],
    broad_context: RawBroadMarketContext,
    market_weather: MarketWeatherSnapshot,
    headline_sentiment_score: Decimal,
    headline_count: int,
    generated_at: datetime,
    option_contract: OptionContractSnapshot | None = None,
) -> CanonicalFeatureVectorV1:
    latest_bar, prior_bar = _required_bars(bars)
    latest_volume = require_observed_count(latest_bar.volume, label="latest bar volume")
    prior_volume = require_observed_count(prior_bar.volume, label="prior bar volume")
    if latest_bar.vwap is None:
        raise MarketDataQualityError("latest bar vwap is unavailable")

    quote_mid = (market_data.bid + market_data.ask) / Decimal("2")
    quote_spread = market_data.ask - market_data.bid
    latest_range = latest_bar.high - latest_bar.low
    prior_range = prior_bar.high - prior_bar.low
    atr_proxy = _positive_or_floor((latest_range + prior_range) / Decimal("2"))

    values: dict[str, Decimal] = {
        "canonical_v1.trend.close_vs_prior_close": _ratio_delta(latest_bar.close, prior_bar.close),
        "canonical_v1.trend.close_position_in_range": _range_position(
            latest_bar.close, latest_bar.low, latest_bar.high
        ),
        "canonical_v1.momentum.intrabar_return": _ratio_delta(latest_bar.close, latest_bar.open),
        "canonical_v1.momentum.last_vs_mid": _ratio_delta(market_data.last, quote_mid),
        "canonical_v1.volatility.latest_range_fraction": latest_range / latest_bar.close,
        "canonical_v1.volatility.atr_proxy_fraction": atr_proxy / latest_bar.close,
        "canonical_v1.liquidity.volume_millions": Decimal(latest_volume) / Decimal("1000000"),
        "canonical_v1.relative_volume.latest_vs_prior": Decimal(latest_volume)
        / _positive_or_floor(Decimal(prior_volume)),
        "canonical_v1.spread.quote_spread_fraction": quote_spread / quote_mid,
        "canonical_v1.gap.open_vs_prior_close": _ratio_delta(latest_bar.open, prior_bar.close),
        "canonical_v1.support.distance_to_recent_low": (market_data.last - latest_bar.low)
        / market_data.last,
        "canonical_v1.resistance.distance_to_recent_high": (latest_bar.high - market_data.last)
        / market_data.last,
        "canonical_v1.vwap.last_vs_vwap": _ratio_delta(market_data.last, latest_bar.vwap),
        "canonical_v1.atr.latest_range_vs_atr_proxy": latest_range / atr_proxy,
        "canonical_v1.index.index_trend_score": broad_context.index_trend_score,
        "canonical_v1.sector.sector_alignment_score": broad_context.sector_alignment_score,
        "canonical_v1.volatility_context.index_level": broad_context.volatility_index_level,
        "canonical_v1.headline.sentiment_pressure": headline_sentiment_score,
        "canonical_v1.headline.count_capped": Decimal(min(headline_count, 10)) / Decimal("10"),
        "canonical_v1.weather.risk_on_score": market_weather.risk_on_score,
        "canonical_v1.weather.breadth_score": market_weather.breadth_score,
        "canonical_v1.weather.regime_risk_on": Decimal("1")
        if market_weather.regime == "risk_on"
        else Decimal("0"),
        "canonical_v1.weather.regime_risk_off": Decimal("1")
        if market_weather.regime == "risk_off"
        else Decimal("0"),
        "canonical_v1.weather.volatility_elevated": Decimal("1")
        if market_weather.volatility_regime == "elevated"
        else Decimal("0"),
    }

    values.update(_option_features(option_contract))
    return CanonicalFeatureVectorV1(
        feature_vector_id=_feature_vector_id(tenant_id, ticker, generated_at, values),
        tenant_id=tenant_id,
        ticker=ticker.upper(),
        feature_values={key: value.quantize(Decimal("0.000001")) for key, value in values.items()},
        generated_at=generated_at,
    )


def _option_features(option_contract: OptionContractSnapshot | None) -> dict[str, Decimal]:
    if option_contract is None:
        return {
            "canonical_v1.options.contract_present": Decimal("0"),
            "canonical_v1.options.liquidity_score": Decimal("0"),
            "canonical_v1.options.greeks_available": Decimal("0"),
            "canonical_v1.options.implied_volatility_available": Decimal("0"),
        }

    mid = (option_contract.bid + option_contract.ask) / Decimal("2")
    spread_fraction = (option_contract.ask - option_contract.bid) / mid
    liquidity_score = min(
        Decimal("1"),
        (Decimal(option_contract.volume) / Decimal("100")) * Decimal("0.40")
        + (Decimal(option_contract.open_interest) / Decimal("500")) * Decimal("0.40")
        + ((Decimal("0.20") - min(spread_fraction, Decimal("0.20"))) / Decimal("0.20"))
        * Decimal("0.20"),
    )
    greeks_available = all(
        value is not None
        for value in (
            option_contract.delta,
            option_contract.gamma,
            option_contract.theta,
            option_contract.vega,
        )
    )
    values = {
        "canonical_v1.options.contract_present": Decimal("1"),
        "canonical_v1.options.spread_fraction": spread_fraction,
        "canonical_v1.options.volume_score": min(
            Decimal("1"), Decimal(option_contract.volume) / Decimal("100")
        ),
        "canonical_v1.options.open_interest_score": min(
            Decimal("1"), Decimal(option_contract.open_interest) / Decimal("500")
        ),
        "canonical_v1.options.liquidity_score": liquidity_score,
        "canonical_v1.options.greeks_available": Decimal("1") if greeks_available else Decimal("0"),
        "canonical_v1.options.implied_volatility_available": Decimal("1")
        if option_contract.implied_volatility is not None
        else Decimal("0"),
    }
    if option_contract.implied_volatility is not None:
        values["canonical_v1.options.implied_volatility"] = option_contract.implied_volatility
    if option_contract.delta is not None:
        values["canonical_v1.options.delta"] = option_contract.delta
    if option_contract.gamma is not None:
        values["canonical_v1.options.gamma"] = option_contract.gamma
    if option_contract.vega is not None:
        values["canonical_v1.options.vega"] = option_contract.vega
    return values


def _required_bars(bars: Sequence[RawStockBar]) -> tuple[RawStockBar, RawStockBar]:
    if len(bars) < 2:
        raise MarketDataQualityError("at least two stock bars are required for feature generation")
    ordered = sorted(bars, key=lambda bar: bar.ended_at, reverse=True)
    return ordered[0], ordered[1]


def _ratio_delta(current: Decimal, baseline: Decimal) -> Decimal:
    return (current - baseline) / _positive_or_floor(baseline)


def _range_position(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    width = high - low
    if width <= Decimal("0"):
        raise MarketDataQualityError("bar high must be greater than low for range features")
    return (value - low) / width


def _positive_or_floor(value: Decimal) -> Decimal:
    return value if value > Decimal("0") else Decimal("0.000001")


def _feature_vector_id(
    tenant_id: str, ticker: str, generated_at: datetime, values: dict[str, Decimal]
) -> str:
    seed = "|".join(f"{key}={values[key]}" for key in sorted(values))
    digest = sha256(
        f"{tenant_id}:{ticker.upper()}:{generated_at.isoformat()}:{seed}".encode()
    ).hexdigest()
    return f"cfv_{digest[:24]}"
