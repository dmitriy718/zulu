from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from zulu_contracts import AssetClass, AssetType, CleanSignalV1


class RiskLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    max_order_notional: Decimal = Field(gt=Decimal("0"))
    max_symbol_exposure: Decimal = Field(gt=Decimal("0"))
    max_risk_per_trade: Decimal = Field(default=Decimal("500"), gt=Decimal("0"))
    max_daily_loss: Decimal = Field(default=Decimal("1000"), gt=Decimal("0"))
    max_weekly_loss: Decimal = Field(default=Decimal("2500"), gt=Decimal("0"))
    max_open_positions: int = Field(default=5, gt=0)
    max_ticker_exposure: Decimal = Field(default=Decimal("25000"), gt=Decimal("0"))
    max_sector_exposure: Decimal | None = Field(default=None, gt=Decimal("0"))
    max_option_contracts: int = Field(default=10, gt=0)
    max_spread_fraction: Decimal = Field(default=Decimal("0.05"), gt=Decimal("0"))
    min_option_open_interest: int = Field(default=1, ge=0)
    min_option_volume: int = Field(default=1, ge=0)
    day_trading_allowed: bool = True
    live_trading_enabled: bool = False


class PortfolioExposure(BaseModel):
    symbol: str = Field(min_length=1)
    current_notional: Decimal = Field(ge=Decimal("0"))


class OrderIntent(BaseModel):
    symbol: str = Field(min_length=1)
    asset_class: AssetClass
    notional: Decimal = Field(gt=Decimal("0"))


class RiskContext(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    now: datetime = Field(default_factory=lambda: datetime.now(UTC))
    order_notional: Decimal = Field(gt=Decimal("0"))
    estimated_max_loss: Decimal = Field(ge=Decimal("0"))
    daily_realized_loss: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    weekly_realized_loss: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    open_positions: int = Field(default=0, ge=0)
    ticker_exposure: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    sector_exposure: Decimal | None = Field(default=None, ge=Decimal("0"))
    requested_quantity: Decimal = Field(gt=Decimal("0"))
    duplicate_signal_or_order: bool = False
    pending_open_conflict: bool = False
    pending_close_conflict: bool = False
    day_trade_count: int = Field(default=0, ge=0)
    day_trade_limit: int | None = Field(default=None, ge=0)
    live_environment: bool = False
    sector_data_available: bool = False
    trade_date: date | None = None

    @field_validator("now")
    @classmethod
    def validate_now(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        return value


class RiskDecision(BaseModel):
    approved: bool
    reason: str
    risk_version: str = "risk-baseline-v1"
    max_loss: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class RiskGate:
    def evaluate(
        self,
        order: OrderIntent,
        exposure: PortfolioExposure,
        limits: RiskLimits,
    ) -> RiskDecision:
        if order.symbol != exposure.symbol:
            return RiskDecision(approved=False, reason="symbol exposure mismatch")
        if order.notional > limits.max_order_notional:
            return RiskDecision(approved=False, reason="order notional exceeds limit")
        projected = exposure.current_notional + order.notional
        if projected > limits.max_symbol_exposure:
            return RiskDecision(approved=False, reason="projected symbol exposure exceeds limit")
        return RiskDecision(approved=True, reason="risk checks passed", max_loss=order.notional)

    def evaluate_signal(
        self,
        signal: CleanSignalV1,
        context: RiskContext,
        limits: RiskLimits,
    ) -> RiskDecision:
        rejection = self._first_rejection(signal, context, limits)
        if rejection is not None:
            return RiskDecision(
                approved=False,
                reason=rejection,
                max_loss=context.estimated_max_loss,
            )
        return RiskDecision(
            approved=True,
            reason="risk checks passed",
            max_loss=context.estimated_max_loss,
        )

    def _first_rejection(
        self,
        signal: CleanSignalV1,
        context: RiskContext,
        limits: RiskLimits,
    ) -> str | None:
        if context.tenant_id != signal.tenant_id:
            return "tenant mismatch"
        if signal.stop_loss <= Decimal("0"):
            return "stop loss is required"
        if not signal.take_profit_levels:
            return "take-profit ladder is required"
        if sum(level.scale_out_fraction for level in signal.take_profit_levels) > Decimal("1"):
            return "take-profit ladder scale-out exceeds one"
        if context.estimated_max_loss > limits.max_risk_per_trade:
            return "max risk per trade exceeded"
        if context.daily_realized_loss + context.estimated_max_loss > limits.max_daily_loss:
            return "max daily loss exceeded"
        if context.weekly_realized_loss + context.estimated_max_loss > limits.max_weekly_loss:
            return "max weekly loss exceeded"
        if context.open_positions >= limits.max_open_positions:
            return "max open positions exceeded"
        if context.ticker_exposure + context.order_notional > limits.max_ticker_exposure:
            return "max ticker exposure exceeded"
        if (
            context.sector_data_available
            and limits.max_sector_exposure is not None
            and context.sector_exposure is not None
            and context.sector_exposure + context.order_notional > limits.max_sector_exposure
        ):
            return "max sector exposure exceeded"
        if _spread_fraction(signal) > limits.max_spread_fraction:
            return "liquidity spread limit exceeded"
        if context.order_notional > limits.max_order_notional:
            return "order notional exceeds limit"
        if context.duplicate_signal_or_order:
            return "duplicate signal or order protection triggered"
        if context.pending_open_conflict:
            return "pending open conflict exists"
        if context.pending_close_conflict:
            return "pending close conflict exists"
        if (
            not limits.day_trading_allowed
            and context.day_trade_limit is not None
            and context.day_trade_count >= context.day_trade_limit
        ):
            return "day-trading restrictions block execution"
        if context.live_environment and not limits.live_trading_enabled:
            return "live environment is not explicitly enabled"
        if signal.asset_type == AssetType.OPTION:
            if signal.option_contract is None:
                return "options execution requires option contract metadata"
            if context.requested_quantity > limits.max_option_contracts:
                return "options contract quantity exceeds limit"
            if signal.option_contract.open_interest < limits.min_option_open_interest:
                return "option open interest below limit"
            if signal.option_contract.volume < limits.min_option_volume:
                return "option volume below limit"
        return None


def _spread_fraction(signal: CleanSignalV1) -> Decimal:
    if signal.asset_type == AssetType.OPTION and signal.option_contract is not None:
        bid = signal.option_contract.bid
        ask = signal.option_contract.ask
    else:
        bid = signal.market_data_snapshot.bid
        ask = signal.market_data_snapshot.ask
    mid = (bid + ask) / Decimal("2")
    return (ask - bid) / mid
