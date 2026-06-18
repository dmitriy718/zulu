from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zulu_api.data.base import Base


def pk(length: int = 80) -> Mapped[str]:
    return mapped_column(String(length), primary_key=True)


def tenant_fk() -> Mapped[str]:
    return mapped_column(String(80), ForeignKey("tenants.tenant_id"), nullable=False, index=True)


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = pk()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    email_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "email_hash", name="uq_users_tenant_email_hash"),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    subscription_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    plan_code: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BrokerConnection(Base):
    __tablename__ = "broker_connections"

    broker_connection_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    user_id: Mapped[str] = mapped_column(String(80), ForeignKey("users.user_id"), nullable=False)
    broker_name: Mapped[str] = mapped_column(String(80), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    credential_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    live_trading_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "live_trading_enabled = false", name="ck_broker_live_trading_default_false"
        ),
    )


class MarketDataSnapshotRow(Base):
    __tablename__ = "market_data_snapshots"

    snapshot_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    bid: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    ask: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    last: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("ask >= bid", name="ck_market_data_ask_gte_bid"),
        CheckConstraint("expires_at > observed_at", name="ck_market_data_expiry"),
        CheckConstraint("volume >= 0", name="ck_market_data_volume_nonnegative"),
        Index("ix_market_data_tenant_ticker_observed", "tenant_id", "ticker", "observed_at"),
    )


class OptionContractSnapshotRow(Base):
    __tablename__ = "option_contract_snapshots"

    option_contract_id: Mapped[str] = pk(120)
    tenant_id: Mapped[str] = tenant_fk()
    underlying_ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    option_symbol: Mapped[str] = mapped_column(String(80), nullable=False)
    option_type: Mapped[str] = mapped_column(String(8), nullable=False)
    strike: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    expiration_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    multiplier: Mapped[int] = mapped_column(Integer, nullable=False)
    bid: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    ask: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    delta: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    gamma: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    theta: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    vega: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    implied_volatility: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    open_interest: Mapped[int] = mapped_column(Integer, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("option_type in ('call', 'put')", name="ck_option_contract_type"),
        CheckConstraint("ask >= bid", name="ck_option_contract_ask_gte_bid"),
        CheckConstraint("expiration_date > observed_at", name="ck_option_contract_expiry"),
        CheckConstraint("multiplier > 0", name="ck_option_contract_multiplier_positive"),
        Index("ix_option_contract_tenant_underlying", "tenant_id", "underlying_ticker"),
    )


class HeadlineEventRow(Base):
    __tablename__ = "headline_events"

    headline_event_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    ticker: Mapped[str | None] = mapped_column(String(12))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000))
    sentiment_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "sentiment_score >= -1 and sentiment_score <= 1", name="ck_headline_sentiment_range"
        ),
        Index("ix_headline_tenant_ticker_published", "tenant_id", "ticker", "published_at"),
    )


class MarketWeatherSnapshotRow(Base):
    __tablename__ = "market_weather_snapshots"

    market_weather_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    regime: Mapped[str] = mapped_column(String(80), nullable=False)
    volatility_regime: Mapped[str] = mapped_column(String(80), nullable=False)
    breadth_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    risk_on_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("expires_at > as_of", name="ck_market_weather_expiry"),
        CheckConstraint("breadth_score >= 0 and breadth_score <= 1", name="ck_weather_breadth"),
        CheckConstraint("risk_on_score >= 0 and risk_on_score <= 1", name="ck_weather_risk_on"),
    )


class FeatureVectorRow(Base):
    __tablename__ = "feature_vectors"

    feature_vector_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    feature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "schema_version", "feature_hash", name="uq_feature_hash"),
        CheckConstraint("feature_values != '{}'::jsonb", name="ck_feature_values_not_empty"),
        Index("ix_feature_vectors_tenant_ticker", "tenant_id", "ticker"),
    )


class StrategyCandidateRow(Base):
    __tablename__ = "strategy_candidates"

    strategy_candidate_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    feature_vector_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("feature_vectors.feature_vector_id"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(String(12), nullable=False)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    direction: Mapped[str] = mapped_column(String(12), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(24), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("asset_type in ('stock', 'option')", name="ck_strategy_asset_type"),
        Index("ix_strategy_candidates_tenant_ticker", "tenant_id", "ticker"),
    )


class CleanSignalRow(Base):
    __tablename__ = "clean_signals"

    signal_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    strategy_candidate_id: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("strategy_candidates.strategy_candidate_id")
    )
    market_data_snapshot_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("market_data_snapshots.snapshot_id"), nullable=False
    )
    option_contract_id: Mapped[str | None] = mapped_column(
        String(120), ForeignKey("option_contract_snapshots.option_contract_id")
    )
    market_weather_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("market_weather_snapshots.market_weather_id"), nullable=False
    )
    feature_vector_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("feature_vectors.feature_vector_id"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(String(12), nullable=False)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    direction: Mapped[str] = mapped_column(String(12), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(24), nullable=False)
    entry_zone: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    entry_trigger: Mapped[str] = mapped_column(Text, nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    take_profit_levels: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    position_sizing_hint: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    quality_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    headline_context: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    technical_context: Mapped[str] = mapped_column(Text, nullable=False)
    volatility_context: Mapped[str] = mapped_column(Text, nullable=False)
    liquidity_context: Mapped[str] = mapped_column(Text, nullable=False)
    upside_thesis: Mapped[str] = mapped_column(Text, nullable=False)
    downside_risk: Mapped[str] = mapped_column(Text, nullable=False)
    invalidation_conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    model_manifest_id: Mapped[str] = mapped_column(String(80), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    feature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_status: Mapped[str] = mapped_column(String(24), nullable=False)
    acceptance_status: Mapped[str] = mapped_column(String(24), nullable=False)
    terminal_state: Mapped[str | None] = mapped_column(String(40))
    decision_trace: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("asset_type in ('stock', 'option')", name="ck_clean_signal_asset_type"),
        CheckConstraint(
            "(asset_type = 'option' and option_contract_id is not null) or "
            "(asset_type = 'stock' and option_contract_id is null)",
            name="ck_clean_signal_option_metadata",
        ),
        CheckConstraint("stop_loss > 0", name="ck_clean_signal_stop_loss"),
        CheckConstraint(
            "entry_zone ? 'lower' and entry_zone ? 'upper'", name="ck_clean_signal_entry_zone"
        ),
        CheckConstraint("length(entry_trigger) > 0", name="ck_clean_signal_entry_trigger"),
        CheckConstraint("jsonb_array_length(take_profit_levels) > 0", name="ck_clean_signal_tp"),
        CheckConstraint(
            "jsonb_array_length(invalidation_conditions) > 0", name="ck_clean_signal_invalidations"
        ),
        CheckConstraint("jsonb_array_length(decision_trace) > 0", name="ck_clean_signal_trace"),
        CheckConstraint("expires_at > created_at", name="ck_clean_signal_expiry"),
        ForeignKeyConstraint(
            ["tenant_id", "feature_schema_version", "feature_hash"],
            [
                "feature_vectors.tenant_id",
                "feature_vectors.schema_version",
                "feature_vectors.feature_hash",
            ],
            name="fk_clean_signal_feature_hash",
        ),
        CheckConstraint(
            "acceptance_status in ('candidate', 'accepted', 'terminal')",
            name="ck_clean_signal_acceptance_status",
        ),
        CheckConstraint(
            "terminal_state is null or terminal_state in ("
            "'delivered_to_signal_station', 'execution_attempted', 'policy_rejected', "
            "'risk_rejected', 'expired', 'cancelled_by_user', 'system_blocked')",
            name="ck_clean_signal_terminal_state",
        ),
        Index("ix_clean_signals_tenant_ticker_created", "tenant_id", "ticker", "created_at"),
    )


class PolicyDecisionRow(Base):
    __tablename__ = "policy_decisions"

    policy_decision_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    signal_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("clean_signals.signal_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("status in ('approved', 'rejected')", name="ck_policy_status"),
    )


class RiskDecisionRow(Base):
    __tablename__ = "risk_decisions"

    risk_decision_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    signal_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("clean_signals.signal_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_version: Mapped[str] = mapped_column(String(80), nullable=False)
    max_loss: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("status in ('approved', 'rejected')", name="ck_risk_status"),
        CheckConstraint("max_loss >= 0", name="ck_risk_max_loss_nonnegative"),
    )


class ExecutionIntentRow(Base):
    __tablename__ = "execution_intents"

    execution_intent_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    signal_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("clean_signals.signal_id"), nullable=False
    )
    policy_decision_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("policy_decisions.policy_decision_id"), nullable=False
    )
    risk_decision_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("risk_decisions.risk_decision_id"), nullable=False
    )
    terminal_state: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("terminal_state = 'execution_attempted'", name="ck_execution_intent_state"),
    )


class BrokerOrderRequestRow(Base):
    __tablename__ = "broker_order_requests"

    broker_order_request_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    execution_intent_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("execution_intents.execution_intent_id"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_broker_order_idempotency"),
        CheckConstraint("length(idempotency_key) >= 16", name="ck_broker_order_idempotency_length"),
        CheckConstraint("quantity > 0", name="ck_broker_order_quantity_positive"),
    )


class SystemIncidentRow(Base):
    __tablename__ = "system_incidents"

    system_incident_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrderLifecycleEventRow(Base):
    __tablename__ = "order_lifecycle_events"

    order_lifecycle_event_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    broker_order_request_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("broker_order_requests.broker_order_request_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    broker_event_id: Mapped[str | None] = mapped_column(String(120))
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    system_incident_id: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("system_incidents.system_incident_id")
    )
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "(reconciled_at is not null or system_incident_id is not null) and "
            "(status != 'unresolved' or system_incident_id is not null)",
            name="ck_order_lifecycle_reconciliation",
        ),
        Index("ix_order_lifecycle_tenant_order", "tenant_id", "broker_order_request_id"),
    )


class PositionRow(Base):
    __tablename__ = "positions"

    position_snapshot_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    ticker: Mapped[str] = mapped_column(String(12), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(12), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    average_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TradeOutcomeRow(Base):
    __tablename__ = "trade_outcomes"

    trade_outcome_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    signal_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("clean_signals.signal_id"), nullable=False
    )
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    max_adverse_excursion: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    max_favorable_excursion: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    labeled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NearMissLabelRow(Base):
    __tablename__ = "near_miss_labels"

    near_miss_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    signal_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("clean_signals.signal_id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    would_have_triggered: Mapped[bool] = mapped_column(nullable=False)
    labeled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelManifestRow(Base):
    __tablename__ = "model_manifests"

    model_manifest_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    training_data_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "model_name", "model_version", name="uq_model_version"),
    )


class ModelEvaluationReportRow(Base):
    __tablename__ = "model_evaluation_reports"

    model_evaluation_report_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    model_manifest_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("model_manifests.model_manifest_id"), nullable=False
    )
    evaluation_window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    evaluation_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    labeled_outcome_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    promotion_approved: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "evaluation_window_end > evaluation_window_start", name="ck_model_eval_window"
        ),
    )


class UserOverrideEventRow(Base):
    __tablename__ = "user_override_events"

    user_override_event_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    user_id: Mapped[str] = mapped_column(String(80), ForeignKey("users.user_id"), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    audit_event_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    actor_id: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    decision: Mapped[str] = mapped_column(String(120), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(120), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("ix_audit_events_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_audit_events_correlation", "correlation_id"),
    )


class OutboxEventRow(Base):
    __tablename__ = "outbox_events"

    outbox_event_id: Mapped[str] = pk()
    tenant_id: Mapped[str] = tenant_fk()
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(120))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_outbox_idempotency"),
        Index("ix_outbox_unprocessed", "tenant_id", "created_at"),
    )
