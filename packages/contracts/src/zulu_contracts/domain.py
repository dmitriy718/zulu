from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictContract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
        use_enum_values=False,
    )


class AssetType(StrEnum):
    STOCK = "stock"
    OPTION = "option"


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


class SignalDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class Timeframe(StrEnum):
    INTRADAY = "intraday"
    SWING = "swing"
    POSITION = "position"


class PolicyStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DecisionStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class AcceptedSignalTerminalState(StrEnum):
    DELIVERED_TO_SIGNAL_STATION = "delivered_to_signal_station"
    EXECUTION_ATTEMPTED = "execution_attempted"
    POLICY_REJECTED = "policy_rejected"
    RISK_REJECTED = "risk_rejected"
    EXPIRED = "expired"
    CANCELLED_BY_USER = "cancelled_by_user"
    SYSTEM_BLOCKED = "system_blocked"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderLifecycleStatus(StrEnum):
    REQUESTED = "requested"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    RECONCILED = "reconciled"
    UNRESOLVED = "unresolved"


class IncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    OPEN = "open"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"


class OverrideAction(StrEnum):
    DISABLE_AUTOMATION = "disable_automation"
    CANCEL_SIGNAL = "cancel_signal"
    BLOCK_INSTRUMENT = "block_instrument"
    RESUME_AUTOMATION = "resume_automation"


def utc_now() -> datetime:
    return datetime.now(UTC)


def require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value


def stable_json_bytes(payload: BaseModel | dict[str, Any]) -> bytes:
    if isinstance(payload, BaseModel):
        encoded = payload.model_dump_json(exclude={"content_hash"}, by_alias=False)
    else:
        encoded = StrictContract.model_validate(payload).model_dump_json()
    return encoded.encode("utf-8")


def feature_hash(
    schema_version: Literal["canonical_features_v1"], feature_values: dict[str, Decimal]
) -> str:
    normalized = "|".join(f"{key}={feature_values[key]}" for key in sorted(feature_values))
    return sha256(f"{schema_version}:{normalized}".encode()).hexdigest()


class EntryZone(StrictContract):
    lower: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    upper: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)

    @model_validator(mode="after")
    def validate_bounds(self) -> EntryZone:
        if self.upper < self.lower:
            raise ValueError("entry zone upper must be greater than or equal to lower")
        return self


class TakeProfitLevel(StrictContract):
    label: str = Field(min_length=1, max_length=64)
    price: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    scale_out_fraction: Decimal = Field(
        gt=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6
    )


class PositionSizingHint(StrictContract):
    max_risk_fraction: Decimal = Field(
        gt=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6
    )
    notional_cap: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=2)
    rationale: str = Field(min_length=1, max_length=500)


class HeadlineContextItem(StrictContract):
    headline_event_id: str = Field(min_length=1, max_length=80)
    relevance: str = Field(min_length=1, max_length=500)


class DecisionTraceItem(StrictContract):
    stage: str = Field(min_length=1, max_length=80)
    decision: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=1000)
    at: datetime = Field(default_factory=utc_now)

    @field_validator("at")
    @classmethod
    def validate_at(cls, value: datetime) -> datetime:
        return require_aware(value)


class MarketDataSnapshot(StrictContract):
    snapshot_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.\-]{0,11}$")
    bid: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    ask: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    last: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    volume: int = Field(ge=0)
    source: str = Field(min_length=1, max_length=120)
    observed_at: datetime
    expires_at: datetime
    received_at: datetime = Field(default_factory=utc_now)

    @field_validator("observed_at", "expires_at", "received_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)

    @model_validator(mode="after")
    def validate_market(self) -> MarketDataSnapshot:
        if self.ask < self.bid:
            raise ValueError("ask must be greater than or equal to bid")
        if self.expires_at <= self.observed_at:
            raise ValueError("market data expiry must be after observed_at")
        return self


class OptionContractSnapshot(StrictContract):
    option_contract_id: str = Field(min_length=1, max_length=120)
    tenant_id: str = Field(min_length=1, max_length=80)
    underlying_ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.\-]{0,11}$")
    option_symbol: str = Field(min_length=1, max_length=80)
    option_type: OptionType
    strike: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    expiration_date: datetime
    multiplier: int = Field(gt=0)
    bid: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    ask: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    delta: Decimal | None = Field(default=None, ge=Decimal("-1"), le=Decimal("1"))
    gamma: Decimal | None = Field(default=None, ge=Decimal("0"))
    theta: Decimal | None = None
    vega: Decimal | None = Field(default=None, ge=Decimal("0"))
    implied_volatility: Decimal | None = Field(default=None, ge=Decimal("0"))
    open_interest: int = Field(ge=0)
    volume: int = Field(ge=0)
    source: str = Field(min_length=1, max_length=120)
    observed_at: datetime

    @field_validator("expiration_date", "observed_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)

    @model_validator(mode="after")
    def validate_option_contract(self) -> OptionContractSnapshot:
        if self.ask < self.bid:
            raise ValueError("option ask must be greater than or equal to bid")
        if self.expiration_date <= self.observed_at:
            raise ValueError("option expiration must be after observation time")
        return self


class HeadlineEvent(StrictContract):
    headline_event_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    ticker: str | None = Field(default=None, max_length=12)
    title: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1, max_length=120)
    url: str | None = Field(default=None, max_length=1000)
    sentiment_score: Decimal = Field(
        ge=Decimal("-1"), le=Decimal("1"), max_digits=8, decimal_places=6
    )
    published_at: datetime
    received_at: datetime = Field(default_factory=utc_now)

    @field_validator("published_at", "received_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class MarketWeatherSnapshot(StrictContract):
    market_weather_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    regime: str = Field(min_length=1, max_length=80)
    volatility_regime: str = Field(min_length=1, max_length=80)
    breadth_score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6)
    risk_on_score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6)
    as_of: datetime
    expires_at: datetime

    @field_validator("as_of", "expires_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)

    @model_validator(mode="after")
    def validate_expiry(self) -> MarketWeatherSnapshot:
        if self.expires_at <= self.as_of:
            raise ValueError("market weather expiry must be after as_of")
        return self


class CanonicalFeatureVectorV1(StrictContract):
    feature_vector_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.\-]{0,11}$")
    schema_version: Literal["canonical_features_v1"] = "canonical_features_v1"
    feature_values: dict[str, Decimal] = Field(min_length=1)
    generated_at: datetime = Field(default_factory=utc_now)

    @field_validator("generated_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)

    @field_validator("feature_values")
    @classmethod
    def validate_features(cls, value: dict[str, Decimal]) -> dict[str, Decimal]:
        if not value:
            raise ValueError("feature vector must not be empty")
        if any(not key.strip() for key in value):
            raise ValueError("feature names must not be blank")
        return value

    @property
    def content_hash(self) -> str:
        return feature_hash(self.schema_version, self.feature_values)


class StrategyCandidate(StrictContract):
    strategy_candidate_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    asset_type: AssetType
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.\-]{0,11}$")
    direction: SignalDirection
    timeframe: Timeframe
    feature_vector: CanonicalFeatureVectorV1
    rationale: str = Field(min_length=20, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class CleanSignalV1(StrictContract):
    signal_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    asset_type: AssetType
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.\-]{0,11}$")
    option_contract: OptionContractSnapshot | None = None
    direction: SignalDirection
    timeframe: Timeframe
    entry_zone: EntryZone
    entry_trigger: str = Field(min_length=1, max_length=1000)
    stop_loss: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    take_profit_levels: list[TakeProfitLevel] = Field(min_length=1)
    position_sizing_hint: PositionSizingHint
    confidence_score: Decimal = Field(
        ge=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6
    )
    risk_score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6)
    quality_score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6)
    market_weather: MarketWeatherSnapshot
    market_data_snapshot: MarketDataSnapshot
    headline_context: list[HeadlineContextItem] = Field(default_factory=list)
    technical_context: str = Field(min_length=1, max_length=2000)
    volatility_context: str = Field(min_length=1, max_length=2000)
    liquidity_context: str = Field(min_length=1, max_length=2000)
    upside_thesis: str = Field(min_length=1, max_length=2000)
    downside_risk: str = Field(min_length=1, max_length=2000)
    invalidation_conditions: list[str] = Field(min_length=1)
    model_manifest_id: str = Field(min_length=1, max_length=80)
    feature_schema_version: Literal["canonical_features_v1"]
    feature_hash: str = Field(min_length=64, max_length=64)
    feature_vector: CanonicalFeatureVectorV1
    policy_status: PolicyStatus
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    decision_trace: list[DecisionTraceItem] = Field(min_length=1)

    @field_validator("created_at", "expires_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)

    @model_validator(mode="after")
    def validate_signal(self) -> CleanSignalV1:
        if self.asset_type == AssetType.OPTION and self.option_contract is None:
            raise ValueError("options signals require option contract metadata")
        if self.asset_type == AssetType.STOCK and self.option_contract is not None:
            raise ValueError("stock signals must not include option contract metadata")
        if self.market_data_snapshot.expires_at <= self.created_at:
            raise ValueError("clean signal cannot use expired market data")
        if self.expires_at <= self.created_at:
            raise ValueError("signal expiry must be after created_at")
        if self.feature_schema_version != self.feature_vector.schema_version:
            raise ValueError("feature schema version must match feature vector schema")
        if self.feature_hash != self.feature_vector.content_hash:
            raise ValueError("feature hash must match feature vector content")
        return self


class PolicyDecision(StrictContract):
    policy_decision_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    signal_id: str = Field(min_length=1, max_length=80)
    status: DecisionStatus
    reason: str = Field(min_length=1, max_length=1000)
    policy_version: str = Field(min_length=1, max_length=80)
    decided_at: datetime = Field(default_factory=utc_now)

    @field_validator("decided_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class RiskDecision(StrictContract):
    risk_decision_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    signal_id: str = Field(min_length=1, max_length=80)
    status: DecisionStatus
    reason: str = Field(min_length=1, max_length=1000)
    risk_version: str = Field(min_length=1, max_length=80)
    max_loss: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=2)
    decided_at: datetime = Field(default_factory=utc_now)

    @field_validator("decided_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class ExecutionIntent(StrictContract):
    execution_intent_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    signal_id: str = Field(min_length=1, max_length=80)
    policy_decision_id: str = Field(min_length=1, max_length=80)
    risk_decision_id: str = Field(min_length=1, max_length=80)
    terminal_state: AcceptedSignalTerminalState
    requested_at: datetime = Field(default_factory=utc_now)

    @field_validator("requested_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class BrokerOrderRequest(StrictContract):
    broker_order_request_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    execution_intent_id: str = Field(min_length=1, max_length=80)
    idempotency_key: str = Field(min_length=16, max_length=120)
    side: OrderSide
    order_type: OrderType
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    limit_price: Decimal | None = Field(
        default=None, gt=Decimal("0"), max_digits=18, decimal_places=6
    )
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class OrderLifecycleEvent(StrictContract):
    order_lifecycle_event_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    broker_order_request_id: str = Field(min_length=1, max_length=80)
    status: OrderLifecycleStatus
    occurred_at: datetime = Field(default_factory=utc_now)
    broker_event_id: str | None = Field(default=None, max_length=120)
    reconciled_at: datetime | None = None
    system_incident_id: str | None = Field(default=None, max_length=80)
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at", "reconciled_at")
    @classmethod
    def validate_timestamp(cls, value: datetime | None) -> datetime | None:
        return require_aware(value) if value is not None else None

    @model_validator(mode="after")
    def validate_reconciliation(self) -> OrderLifecycleEvent:
        if self.reconciled_at is None and self.system_incident_id is None:
            raise ValueError("execution events require reconciliation or an unresolved incident")
        if self.status == OrderLifecycleStatus.UNRESOLVED and self.system_incident_id is None:
            raise ValueError("unresolved execution events require a system incident")
        return self


class PositionSnapshot(StrictContract):
    position_snapshot_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.\-]{0,11}$")
    asset_type: AssetType
    quantity: Decimal = Field(max_digits=18, decimal_places=6)
    average_price: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    market_value: Decimal = Field(max_digits=18, decimal_places=2)
    as_of: datetime

    @field_validator("as_of")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class TradeOutcomeLabel(StrictContract):
    trade_outcome_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    signal_id: str = Field(min_length=1, max_length=80)
    realized_pnl: Decimal = Field(max_digits=18, decimal_places=2)
    max_adverse_excursion: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=2)
    max_favorable_excursion: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=2)
    label: str = Field(min_length=1, max_length=80)
    labeled_at: datetime = Field(default_factory=utc_now)

    @field_validator("labeled_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class NearMissLabel(StrictContract):
    near_miss_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    signal_id: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=1000)
    would_have_triggered: bool
    labeled_at: datetime = Field(default_factory=utc_now)

    @field_validator("labeled_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class ModelManifest(StrictContract):
    model_manifest_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    model_name: str = Field(min_length=1, max_length=120)
    model_version: str = Field(min_length=1, max_length=80)
    feature_schema_version: Literal["canonical_features_v1"]
    artifact_uri: str = Field(min_length=1, max_length=500)
    training_data_hash: str = Field(min_length=64, max_length=64)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class ModelEvaluationReport(StrictContract):
    model_evaluation_report_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    model_manifest_id: str = Field(min_length=1, max_length=80)
    evaluation_window_start: datetime
    evaluation_window_end: datetime
    labeled_outcome_count: int = Field(ge=0)
    metrics: dict[str, Decimal] = Field(min_length=1)
    promotion_approved: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("evaluation_window_start", "evaluation_window_end", "created_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)

    @model_validator(mode="after")
    def validate_window(self) -> ModelEvaluationReport:
        if self.evaluation_window_end <= self.evaluation_window_start:
            raise ValueError("evaluation window end must be after start")
        return self


class UserOverrideEvent(StrictContract):
    user_override_event_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    user_id: str = Field(min_length=1, max_length=80)
    action: OverrideAction
    reason: str = Field(min_length=1, max_length=1000)
    occurred_at: datetime = Field(default_factory=utc_now)

    @field_validator("occurred_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)


class SystemIncident(StrictContract):
    system_incident_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    severity: IncidentSeverity
    status: IncidentStatus
    summary: str = Field(min_length=1, max_length=500)
    opened_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None

    @field_validator("opened_at", "resolved_at")
    @classmethod
    def validate_timestamp(cls, value: datetime | None) -> datetime | None:
        return require_aware(value) if value is not None else None

    @model_validator(mode="after")
    def validate_resolution(self) -> SystemIncident:
        if self.status == IncidentStatus.RESOLVED and self.resolved_at is None:
            raise ValueError("resolved incidents require resolved_at")
        return self


class AuditEvent(StrictContract):
    audit_event_id: str = Field(min_length=1, max_length=80)
    tenant_id: str = Field(min_length=1, max_length=80)
    actor_id: str = Field(min_length=1, max_length=80)
    action: str = Field(min_length=1, max_length=120)
    entity_type: str = Field(min_length=1, max_length=120)
    entity_id: str = Field(min_length=1, max_length=120)
    decision: str = Field(min_length=1, max_length=120)
    correlation_id: str = Field(min_length=1, max_length=120)
    occurred_at: datetime = Field(default_factory=utc_now)
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return require_aware(value)
