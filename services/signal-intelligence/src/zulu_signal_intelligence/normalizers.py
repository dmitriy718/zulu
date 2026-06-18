from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from ipaddress import ip_address
from urllib.parse import urlparse

from zulu_contracts import (
    HeadlineEvent,
    MarketDataSnapshot,
    MarketWeatherSnapshot,
    OptionContractSnapshot,
)

from zulu_signal_intelligence.constraints import (
    MarketDataConstraints,
    MarketDataQualityError,
    reject_stale,
    reject_wide_spread,
    require_observed_count,
)
from zulu_signal_intelligence.provider_models import (
    RawBroadMarketContext,
    RawHeadline,
    RawMarketCalendar,
    RawOptionContract,
    RawStockBar,
    RawStockQuote,
)

OCC_SYMBOL_PATTERN = re.compile(r"^([A-Z]{1,6})(\d{6})([CP])(\d{8})$")


def normalize_stock_quote(
    raw: RawStockQuote,
    *,
    tenant_id: str,
    now: datetime,
    constraints: MarketDataConstraints | None = None,
) -> MarketDataSnapshot:
    active_constraints = constraints or MarketDataConstraints()
    reject_stale(
        observed_at=raw.observed_at,
        now=now,
        max_age=active_constraints.max_quote_age,
        label="stock quote",
    )
    reject_wide_spread(
        bid=raw.bid,
        ask=raw.ask,
        max_fraction=active_constraints.max_spread_fraction,
        label="stock quote",
    )
    volume = require_observed_count(raw.volume, label="stock quote volume")
    if volume < active_constraints.min_stock_volume:
        raise MarketDataQualityError("stock quote volume is below configured liquidity floor")
    ticker = raw.ticker.upper()
    return MarketDataSnapshot(
        snapshot_id=f"md_{sha256(raw.provenance.source_label.encode()).hexdigest()[:24]}",
        tenant_id=tenant_id,
        ticker=ticker,
        bid=raw.bid,
        ask=raw.ask,
        last=raw.last,
        volume=volume,
        source=raw.provenance.source_label,
        observed_at=raw.observed_at,
        expires_at=raw.observed_at + active_constraints.max_quote_age,
        received_at=raw.provenance.retrieved_at,
    )


def normalize_stock_bars(
    raw_bars: list[RawStockBar],
    *,
    now: datetime,
    constraints: MarketDataConstraints | None = None,
) -> tuple[RawStockBar, ...]:
    active_constraints = constraints or MarketDataConstraints()
    if len(raw_bars) < 2:
        raise MarketDataQualityError("at least two stock bars are required")

    seen_sources: set[str] = set()
    seen_end_times: set[datetime] = set()
    for bar in raw_bars:
        if bar.provenance.source_label in seen_sources:
            raise MarketDataQualityError("duplicate stock bar provider record")
        if bar.ended_at in seen_end_times:
            raise MarketDataQualityError("duplicate stock bar end timestamp")
        seen_sources.add(bar.provenance.source_label)
        seen_end_times.add(bar.ended_at)
        require_observed_count(bar.volume, label="stock bar volume")
        if bar.vwap is None:
            raise MarketDataQualityError("stock bar vwap is unavailable")

    ordered = tuple(sorted(raw_bars, key=lambda bar: bar.ended_at, reverse=True))
    reject_stale(
        observed_at=ordered[0].ended_at,
        now=now,
        max_age=active_constraints.max_stock_bar_age,
        label="stock bars",
    )
    return ordered


def normalize_option_contract(
    raw: RawOptionContract,
    *,
    tenant_id: str,
    now: datetime,
    constraints: MarketDataConstraints | None = None,
) -> OptionContractSnapshot:
    active_constraints = constraints or MarketDataConstraints()
    _validate_occ_option_symbol(raw)
    reject_stale(
        observed_at=raw.observed_at,
        now=now,
        max_age=active_constraints.max_option_age,
        label="option contract",
    )
    reject_wide_spread(
        bid=raw.bid,
        ask=raw.ask,
        max_fraction=active_constraints.max_spread_fraction,
        label="option contract",
    )
    volume = require_observed_count(raw.volume, label="option volume")
    open_interest = require_observed_count(raw.open_interest, label="option open interest")
    if volume < active_constraints.min_option_volume:
        raise MarketDataQualityError("option volume is below configured liquidity floor")
    if open_interest < active_constraints.min_option_open_interest:
        raise MarketDataQualityError("option open interest is below configured liquidity floor")
    return OptionContractSnapshot(
        option_contract_id=f"opt_{sha256(raw.provenance.source_label.encode()).hexdigest()[:24]}",
        tenant_id=tenant_id,
        underlying_ticker=raw.underlying_ticker.upper(),
        option_symbol=raw.option_symbol.upper(),
        option_type=raw.option_type,
        strike=raw.strike,
        expiration_date=raw.expiration_date,
        multiplier=raw.multiplier,
        bid=raw.bid,
        ask=raw.ask,
        delta=raw.delta,
        gamma=raw.gamma,
        theta=raw.theta,
        vega=raw.vega,
        implied_volatility=raw.implied_volatility,
        open_interest=open_interest,
        volume=volume,
        source=raw.provenance.source_label,
        observed_at=raw.observed_at,
    )


def _validate_occ_option_symbol(raw: RawOptionContract) -> None:
    option_symbol = raw.option_symbol.upper()
    match = OCC_SYMBOL_PATTERN.fullmatch(option_symbol)
    if match is None:
        raise MarketDataQualityError("option symbol must use supported OCC format")
    root, expiration, option_type, strike = match.groups()
    if root.rstrip() != raw.underlying_ticker.upper():
        raise MarketDataQualityError("option symbol underlying does not match provider metadata")
    if expiration != raw.expiration_date.strftime("%y%m%d"):
        raise MarketDataQualityError("option symbol expiration does not match provider metadata")
    expected_type = "C" if raw.option_type.value == "call" else "P"
    if option_type != expected_type:
        raise MarketDataQualityError("option symbol type does not match provider metadata")
    parsed_strike = (Decimal(strike) / Decimal("1000")).quantize(Decimal("0.001"))
    if parsed_strike != raw.strike.quantize(Decimal("0.001")):
        raise MarketDataQualityError("option symbol strike does not match provider metadata")


def normalize_headlines(
    raw_headlines: list[RawHeadline],
    *,
    tenant_id: str,
    now: datetime,
    constraints: MarketDataConstraints | None = None,
) -> list[HeadlineEvent]:
    active_constraints = constraints or MarketDataConstraints()
    seen_keys: set[str] = set()
    events: list[HeadlineEvent] = []
    for raw in raw_headlines:
        if raw.published_at is None or raw.source_name is None:
            continue
        if raw.url is not None and not is_safe_headline_url(raw.url):
            continue
        reject_stale(
            observed_at=raw.published_at,
            now=now,
            max_age=active_constraints.max_headline_age,
            label="headline",
        )
        dedupe_key = (raw.url or f"{raw.source_name}:{raw.title}").lower()
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        ticker = raw.tickers[0].upper() if raw.tickers else None
        sentiment_score = classify_headline_sentiment(raw.title)
        events.append(
            HeadlineEvent(
                headline_event_id=f"headline_{sha256(dedupe_key.encode()).hexdigest()[:24]}",
                tenant_id=tenant_id,
                ticker=ticker,
                title=raw.title,
                source=f"{raw.source_name}:{raw.provenance.source_label}",
                url=raw.url,
                sentiment_score=sentiment_score,
                published_at=raw.published_at,
                received_at=raw.provenance.retrieved_at,
            )
        )
    return sorted(events, key=lambda event: event.published_at, reverse=True)


def classify_headline_category(title: str) -> str:
    lowered = title.lower()
    if "earnings" in lowered or "quarter" in lowered:
        return "earnings"
    if "guidance" in lowered or "outlook" in lowered:
        return "guidance"
    if "upgrade" in lowered or "downgrade" in lowered:
        return "analyst_action"
    return "general"


def conservative_catalyst_summary(headline: RawHeadline) -> str:
    category = classify_headline_category(headline.title)
    verification = (
        "unverified_metadata"
        if headline.published_at is None or headline.source_name is None
        else "provider_metadata_present"
    )
    summary_state = "summary_present" if headline.summary else "summary_unavailable"
    return f"{category}; {verification}; {summary_state}; {headline.title[:180]}"


def is_safe_headline_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.hostname is None:
        return False
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"}:
        return False
    try:
        address = ip_address(host)
    except ValueError:
        return True
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    )


def classify_headline_sentiment(title: str) -> Decimal:
    lowered = title.lower()
    if any(term in lowered for term in ("beats", "raises", "upgrade", "growth", "steady")):
        return Decimal("0.25")
    if any(term in lowered for term in ("misses", "cuts", "downgrade", "probe", "risk")):
        return Decimal("-0.25")
    return Decimal("0")


def normalize_market_weather(
    context: RawBroadMarketContext,
    calendar: RawMarketCalendar,
    headlines: list[HeadlineEvent],
    *,
    tenant_id: str,
    now: datetime,
) -> MarketWeatherSnapshot:
    reject_stale(
        observed_at=calendar.session_date,
        now=now,
        max_age=MarketDataConstraints().max_calendar_age,
        label="market calendar",
    )
    reject_stale(
        observed_at=context.observed_at,
        now=now,
        max_age=timedelta(minutes=5),
        label="broad market context",
    )
    headline_pressure = Decimal("0")
    if headlines:
        headline_pressure = sum(
            (headline.sentiment_score for headline in headlines), Decimal("0")
        ) / Decimal(len(headlines))
    risk_on_score = clamp01(
        (context.risk_on_score * Decimal("0.45"))
        + ((context.index_trend_score + Decimal("1")) / Decimal("2") * Decimal("0.25"))
        + (context.breadth_score * Decimal("0.20"))
        + ((headline_pressure + Decimal("1")) / Decimal("2") * Decimal("0.10"))
    )
    volatility_regime = "elevated" if context.volatility_index_level >= Decimal("25") else "normal"
    regime = "risk_on" if risk_on_score >= Decimal("0.60") else "balanced"
    if risk_on_score <= Decimal("0.40"):
        regime = "risk_off"
    source_seed = (
        f"{context.provenance.source_label}:{calendar.provenance.source_label}:{now.isoformat()}"
    )
    return MarketWeatherSnapshot(
        market_weather_id=f"mw_{sha256(source_seed.encode()).hexdigest()[:24]}",
        tenant_id=tenant_id,
        regime=regime,
        volatility_regime=volatility_regime,
        breadth_score=context.breadth_score,
        risk_on_score=risk_on_score,
        as_of=now,
        expires_at=now + timedelta(minutes=5),
    )


def clamp01(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("1"), value.quantize(Decimal("0.000001"))))
