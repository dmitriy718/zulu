from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator
from zulu_contracts import AssetType, CleanSignalV1


class ExecutionEnvironment(StrEnum):
    PAPER = "paper"
    SHADOW = "shadow"
    LIVE = "live"


class SubscriptionMode(StrEnum):
    SIGNAL_ONLY = "signal_only"
    PAPER_AUTOMATION = "paper_automation"
    LIVE_AUTOMATION = "live_automation"


class MarketSessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"


class ModelManifestStatus(StrEnum):
    APPROVED = "approved"
    BASELINE = "baseline"
    DISABLED = "disabled"


class FeatureSchemaStatus(StrEnum):
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class DataQualityStatus(StrEnum):
    PASSING = "passing"
    DEGRADED = "degraded"
    FAILING = "failing"


class OverrideStatus(StrEnum):
    NONE = "none"
    DISABLE_AUTOMATION = "disable_automation"
    CANCEL_SIGNAL = "cancel_signal"
    BLOCK_INSTRUMENT = "block_instrument"


class PolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    live_trading_enabled: bool = False
    user_approved_signal: bool = False
    instrument_allowed: bool = False
    policy_version: str = Field(min_length=1)


class PolicyContext(PolicyInput):
    subscription_mode: SubscriptionMode = SubscriptionMode.SIGNAL_ONLY
    user_automation_permission: bool = False
    environment: ExecutionEnvironment = ExecutionEnvironment.PAPER
    supported_asset_types: frozenset[AssetType] = Field(
        default_factory=lambda: frozenset({AssetType.STOCK})
    )
    now: datetime = Field(default_factory=lambda: datetime.now(UTC))
    market_session_status: MarketSessionStatus = MarketSessionStatus.OPEN
    restricted_tickers: frozenset[str] = Field(default_factory=frozenset)
    restricted_contracts: frozenset[str] = Field(default_factory=frozenset)
    model_manifest_status: ModelManifestStatus = ModelManifestStatus.BASELINE
    feature_schema_status: FeatureSchemaStatus = FeatureSchemaStatus.APPROVED
    data_quality_status: DataQualityStatus = DataQualityStatus.PASSING
    incident_mode_active: bool = False
    kill_switch_active: bool = False
    compliance_copy_present: bool = True
    user_override_status: OverrideStatus = OverrideStatus.NONE

    @field_validator("now")
    @classmethod
    def validate_now(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        return value


class PolicyDecision(BaseModel):
    approved: bool
    reason: str
    policy_version: str
    action: str = "blocked"


class PolicyGate:
    def evaluate(
        self,
        policy_input: PolicyInput | PolicyContext,
        signal: CleanSignalV1 | None = None,
    ) -> PolicyDecision:
        if signal is None and not isinstance(policy_input, PolicyContext):
            return self._evaluate_legacy(policy_input)
        context = (
            policy_input
            if isinstance(policy_input, PolicyContext)
            else PolicyContext(**policy_input.model_dump())
        )
        if signal is None:
            return PolicyDecision(
                approved=False,
                reason="clean signal is required for policy evaluation",
                policy_version=context.policy_version,
                action="blocked",
            )
        rejection = self._first_rejection(context, signal)
        if rejection is not None:
            return PolicyDecision(
                approved=False,
                reason=rejection,
                policy_version=context.policy_version,
                action="blocked",
            )
        return PolicyDecision(
            approved=True,
            reason="policy checks passed",
            policy_version=context.policy_version,
            action="routed",
        )

    def _evaluate_legacy(self, policy_input: PolicyInput) -> PolicyDecision:
        if not policy_input.user_approved_signal:
            return PolicyDecision(
                approved=False,
                reason="signal requires explicit user approval",
                policy_version=policy_input.policy_version,
            )
        if not policy_input.instrument_allowed:
            return PolicyDecision(
                approved=False,
                reason="instrument is outside tenant policy",
                policy_version=policy_input.policy_version,
            )
        return PolicyDecision(
            approved=True,
            reason="policy checks passed",
            policy_version=policy_input.policy_version,
            action="routed",
        )

    def _first_rejection(self, context: PolicyContext, signal: CleanSignalV1) -> str | None:
        if context.tenant_id != signal.tenant_id:
            return "tenant mismatch"
        if context.kill_switch_active:
            return "kill switch is active"
        if context.incident_mode_active:
            return "incident mode is active"
        if context.user_override_status != OverrideStatus.NONE:
            return f"user override blocks automation: {context.user_override_status.value}"
        if not context.compliance_copy_present:
            return "required compliance copy is missing"
        if not context.user_approved_signal:
            return "signal requires explicit user approval"
        if not context.instrument_allowed:
            return "instrument is outside tenant policy"
        if not context.user_automation_permission:
            return "user lacks automation permission"
        if signal.asset_type not in context.supported_asset_types:
            return "asset type is not supported by tenant policy"
        if (
            signal.expires_at <= context.now
            or signal.market_data_snapshot.expires_at <= context.now
        ):
            return "signal or market data is stale"
        if context.market_session_status != MarketSessionStatus.OPEN:
            return "market session is not open"
        if signal.ticker in context.restricted_tickers:
            return "ticker is restricted"
        if (
            signal.option_contract is not None
            and signal.option_contract.option_symbol in context.restricted_contracts
        ):
            return "option contract is restricted"
        if context.model_manifest_status == ModelManifestStatus.DISABLED:
            return "model manifest is disabled"
        if context.feature_schema_status != FeatureSchemaStatus.APPROVED:
            return "feature schema is not approved"
        if context.data_quality_status == DataQualityStatus.FAILING:
            return "data quality status is failing"
        if signal.market_weather.regime == "risk_off":
            return "market weather risk state blocks automation"
        if context.environment == ExecutionEnvironment.LIVE:
            if context.subscription_mode != SubscriptionMode.LIVE_AUTOMATION:
                return "tenant subscription does not allow live automation"
            if not context.live_trading_enabled:
                return "live trading is not explicitly enabled"
        elif context.subscription_mode == SubscriptionMode.SIGNAL_ONLY:
            return "tenant subscription does not allow automation"
        return None
