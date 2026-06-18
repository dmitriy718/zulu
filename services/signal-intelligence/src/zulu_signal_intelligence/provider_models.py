from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from zulu_contracts.domain import OptionType, require_aware


class ProviderCapability(StrEnum):
    STOCK_QUOTES = "stock_quotes"
    STOCK_TRADES = "stock_trades"
    STOCK_BARS = "stock_bars"
    OPTIONS_CHAIN = "options_chain"
    OPTIONS_QUOTES = "options_quotes"
    OPTIONS_TRADES = "options_trades"
    OPTIONS_GREEKS = "options_greeks"
    OPTIONS_IMPLIED_VOLATILITY = "options_implied_volatility"
    OPTIONS_OPEN_INTEREST = "options_open_interest"
    HEADLINES = "headlines"
    MARKET_CALENDAR = "market_calendar"
    INDEX_CONTEXT = "index_context"
    SECTOR_CONTEXT = "sector_context"
    VOLATILITY_CONTEXT = "volatility_context"


class ProviderHealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class MarketSessionState(StrEnum):
    PRE_MARKET = "pre_market"
    OPEN = "open"
    POST_MARKET = "post_market"
    CLOSED = "closed"


class DataQualityStatus(StrEnum):
    PASS = "pass"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class RawProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)


class ProviderHealth(RawProviderModel):
    provider_name: str = Field(min_length=1, max_length=120)
    state: ProviderHealthState
    checked_at: datetime
    detail: str = Field(min_length=1, max_length=500)

    @field_validator("checked_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class ProviderCapabilities(RawProviderModel):
    provider_name: str = Field(min_length=1, max_length=120)
    capabilities: frozenset[ProviderCapability]

    def supports(self, capability: ProviderCapability) -> bool:
        return capability in self.capabilities


class ProviderProvenance(RawProviderModel):
    provider_name: str = Field(min_length=1, max_length=120)
    provider_mode: str = Field(min_length=1, max_length=40)
    provider_record_id: str = Field(min_length=1, max_length=160)
    retrieved_at: datetime

    @field_validator("retrieved_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)

    @property
    def source_label(self) -> str:
        return f"{self.provider_name}:{self.provider_mode}:{self.provider_record_id}"


class DataQualityMetadata(RawProviderModel):
    status: DataQualityStatus
    code: str = Field(min_length=1, max_length=80)
    detail: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1, max_length=200)
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class RawStockQuote(RawProviderModel):
    ticker: str = Field(min_length=1, max_length=12)
    bid: Decimal = Field(gt=Decimal("0"))
    ask: Decimal = Field(gt=Decimal("0"))
    last: Decimal = Field(gt=Decimal("0"))
    volume: int | None = Field(default=None, ge=0)
    observed_at: datetime
    provenance: ProviderProvenance

    @field_validator("observed_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)

    @model_validator(mode="after")
    def validate_quote(self) -> RawStockQuote:
        if self.ask < self.bid:
            raise ValueError("ask must be greater than or equal to bid")
        return self


class RawStockTrade(RawProviderModel):
    ticker: str = Field(min_length=1, max_length=12)
    price: Decimal = Field(gt=Decimal("0"))
    size: int = Field(gt=0)
    traded_at: datetime
    provenance: ProviderProvenance

    @field_validator("traded_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class RawStockBar(RawProviderModel):
    ticker: str = Field(min_length=1, max_length=12)
    open: Decimal = Field(gt=Decimal("0"))
    high: Decimal = Field(gt=Decimal("0"))
    low: Decimal = Field(gt=Decimal("0"))
    close: Decimal = Field(gt=Decimal("0"))
    volume: int | None = Field(default=None, ge=0)
    vwap: Decimal | None = Field(default=None, gt=Decimal("0"))
    started_at: datetime
    ended_at: datetime
    provenance: ProviderProvenance

    @field_validator("started_at", "ended_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)

    @model_validator(mode="after")
    def validate_bar(self) -> RawStockBar:
        if self.ended_at <= self.started_at:
            raise ValueError("stock bar ended_at must be after started_at")
        if self.high < self.low:
            raise ValueError("stock bar high must be greater than or equal to low")
        for label, value in {
            "open": self.open,
            "close": self.close,
            "vwap": self.vwap,
        }.items():
            if value is not None and not self.low <= value <= self.high:
                raise ValueError(f"stock bar {label} must be inside high/low range")
        return self


class RawOptionContract(RawProviderModel):
    underlying_ticker: str = Field(min_length=1, max_length=12)
    option_symbol: str = Field(min_length=1, max_length=80)
    option_type: OptionType
    strike: Decimal = Field(gt=Decimal("0"))
    expiration_date: datetime
    multiplier: int = Field(gt=0)
    bid: Decimal = Field(gt=Decimal("0"))
    ask: Decimal = Field(gt=Decimal("0"))
    delta: Decimal | None = Field(default=None, ge=Decimal("-1"), le=Decimal("1"))
    gamma: Decimal | None = Field(default=None, ge=Decimal("0"))
    theta: Decimal | None = None
    vega: Decimal | None = Field(default=None, ge=Decimal("0"))
    implied_volatility: Decimal | None = Field(default=None, ge=Decimal("0"))
    open_interest: int | None = Field(default=None, ge=0)
    volume: int | None = Field(default=None, ge=0)
    observed_at: datetime
    provenance: ProviderProvenance

    @field_validator("expiration_date", "observed_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)

    @model_validator(mode="after")
    def validate_contract(self) -> RawOptionContract:
        if self.ask < self.bid:
            raise ValueError("option ask must be greater than or equal to bid")
        if self.expiration_date <= self.observed_at:
            raise ValueError("option expiration must be after observation time")
        return self


class RawHeadline(RawProviderModel):
    provider_headline_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=500)
    source_name: str | None = Field(default=None, max_length=120)
    url: str | None = Field(default=None, max_length=1000)
    published_at: datetime | None = None
    tickers: list[str] = Field(default_factory=list)
    summary: str | None = Field(default=None, max_length=1000)
    provenance: ProviderProvenance

    @field_validator("published_at")
    @classmethod
    def validate_optional_timestamp(cls, value: datetime | None) -> datetime | None:
        return require_aware(value) if value is not None else None


class RawMarketCalendar(RawProviderModel):
    session_state: MarketSessionState
    session_date: datetime
    next_open_at: datetime | None = None
    next_close_at: datetime | None = None
    provenance: ProviderProvenance

    @field_validator("session_date", "next_open_at", "next_close_at")
    @classmethod
    def validate_timestamp(cls, value: datetime | None) -> datetime | None:
        return require_aware(value) if value is not None else None


class RawBroadMarketContext(RawProviderModel):
    index_trend_score: Decimal = Field(ge=Decimal("-1"), le=Decimal("1"))
    sector_alignment_score: Decimal = Field(ge=Decimal("-1"), le=Decimal("1"))
    volatility_index_level: Decimal = Field(gt=Decimal("0"))
    breadth_score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    liquidity_score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    risk_on_score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    observed_at: datetime
    provenance: ProviderProvenance

    @field_validator("observed_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)
