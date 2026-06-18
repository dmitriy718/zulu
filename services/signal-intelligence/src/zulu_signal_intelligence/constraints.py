from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal


class MarketDataQualityError(ValueError):
    pass


@dataclass(frozen=True)
class MarketDataConstraints:
    max_quote_age: timedelta = timedelta(seconds=30)
    max_stock_bar_age: timedelta = timedelta(minutes=5)
    max_option_age: timedelta = timedelta(minutes=2)
    max_headline_age: timedelta = timedelta(days=7)
    max_calendar_age: timedelta = timedelta(minutes=5)
    max_spread_fraction: Decimal = Decimal("0.05")
    min_stock_volume: int = 1
    min_option_volume: int = 1
    min_option_open_interest: int = 1


def reject_stale(*, observed_at: datetime, now: datetime, max_age: timedelta, label: str) -> None:
    if observed_at > now:
        raise MarketDataQualityError(f"{label} timestamp is in the future")
    if now - observed_at > max_age:
        raise MarketDataQualityError(f"{label} is stale")


def reject_wide_spread(*, bid: Decimal, ask: Decimal, max_fraction: Decimal, label: str) -> None:
    midpoint = (bid + ask) / Decimal("2")
    spread_fraction = (ask - bid) / midpoint
    if spread_fraction > max_fraction:
        raise MarketDataQualityError(f"{label} spread exceeds configured limit")


def require_observed_count(value: int | None, *, label: str) -> int:
    if value is None:
        raise MarketDataQualityError(f"{label} is unavailable and requires an explicit policy rule")
    return value
