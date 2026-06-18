from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from zulu_contracts import AuditEvent
from zulu_contracts.domain import IncidentSeverity, IncidentStatus, SystemIncident


class ProductMode(StrEnum):
    SIGNAL_STATION = "signal_station"
    AUTOMATION_STATION = "automation_station"


class PlanCode(StrEnum):
    SIGNAL_BASIC = "signal_basic"
    AUTOMATION_PAPER = "automation_paper"
    AUTOMATION_LIVE = "automation_live"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PENDING_CHANGE = "pending_change"
    CANCELLED = "cancelled"


class AutomationEnvironment(StrEnum):
    PAPER = "paper"
    SHADOW = "shadow"
    LIVE = "live"


class PageParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=120)


class TenantSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    display_name: str = Field(min_length=1, max_length=160)
    risk_disclosure_acknowledged: bool = False
    provider_data_disclaimer_acknowledged: bool = False


class PlanStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    plan_code: PlanCode
    status: SubscriptionStatus
    allowed_modes: tuple[ProductMode, ...]
    automation_enabled: bool
    live_trading_allowed: bool


class PlanChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_plan: PlanCode
    idempotency_key: str = Field(min_length=12, max_length=120)


class PlanChangeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool
    status: str
    reason: str
    billing_reference: str


class AutomationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    environment: AutomationEnvironment = AutomationEnvironment.PAPER
    paper_enabled: bool = True
    shadow_enabled: bool = False
    live_enabled: bool = False
    risk_envelope_id: str = "risk_default"
    disclosure: str = (
        "Stocks and options automation carries risk. Signals are informational; "
        "automation remains user-directed and gate-controlled."
    )


class BrokerConnectionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    broker_name: str
    connected: bool
    environment: AutomationEnvironment
    credential_configured: bool
    account_id_redacted: str | None = None


class SignalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    tenant_id: str
    ticker: str
    status: str
    acknowledged: bool = False
    confidence_score: Decimal = Decimal("0.620000")
    risk_score: Decimal = Decimal("0.210000")
    uncertainty_note: str = "Model outputs are uncertain and depend on available data."


class SignalDetail(SignalSummary):
    market_context: dict[str, str]
    data_limitations: tuple[str, ...]
    risk_disclosure: str


class SignalAcknowledgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acknowledged: bool
    client_request_id: str = Field(min_length=8, max_length=120)


class KillSwitchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: str = Field(min_length=1, max_length=40)
    target: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=500)


@dataclass
class PlatformStore:
    tenant_settings: dict[str, TenantSettings] = field(default_factory=dict)
    subscriptions: dict[str, PlanStatus] = field(default_factory=dict)
    automation_settings: dict[str, AutomationSettings] = field(default_factory=dict)
    broker_connections: dict[str, BrokerConnectionStatus] = field(default_factory=dict)
    signals: dict[str, list[SignalSummary]] = field(default_factory=dict)
    audit_events: dict[str, list[AuditEvent]] = field(default_factory=dict)
    incidents: dict[str, list[SystemIncident]] = field(default_factory=dict)
    kill_switches: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    @classmethod
    def fixture(cls) -> PlatformStore:
        now = datetime.now(UTC)
        store = cls()
        for tenant_id, name, plan in (
            ("tenant_1", "Zulu Demo Tenant", PlanCode.AUTOMATION_PAPER),
            ("tenant_2", "Zulu Other Tenant", PlanCode.SIGNAL_BASIC),
        ):
            store.tenant_settings[tenant_id] = TenantSettings(
                tenant_id=tenant_id,
                display_name=name,
                risk_disclosure_acknowledged=True,
                provider_data_disclaimer_acknowledged=True,
            )
            store.subscriptions[tenant_id] = _plan_status(tenant_id, plan)
            store.automation_settings[tenant_id] = AutomationSettings(tenant_id=tenant_id)
            store.broker_connections[tenant_id] = BrokerConnectionStatus(
                tenant_id=tenant_id,
                broker_name="paper",
                connected=plan != PlanCode.SIGNAL_BASIC,
                environment=AutomationEnvironment.PAPER,
                credential_configured=False,
            )
            store.signals[tenant_id] = [
                SignalSummary(
                    signal_id=f"signal_{tenant_id}_1",
                    tenant_id=tenant_id,
                    ticker="MSFT",
                    status="delivered_to_signal_station",
                )
            ]
            store.incidents[tenant_id] = [
                SystemIncident(
                    system_incident_id=f"incident_{tenant_id}_provider",
                    tenant_id=tenant_id,
                    severity=IncidentSeverity.LOW,
                    status=IncidentStatus.OPEN,
                    summary="fixture provider latency incident",
                    opened_at=now - timedelta(minutes=5),
                )
            ]
        return store

    def append_audit(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        action: str,
        decision: str,
        correlation_id: str,
        details: dict[str, Any],
    ) -> AuditEvent:
        event = AuditEvent(
            audit_event_id=_id("audit", tenant_id, actor_id, action, correlation_id),
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            entity_type="platform_control",
            entity_id=tenant_id,
            decision=decision,
            correlation_id=correlation_id,
            details=_redact_details(details),
        )
        self.audit_events.setdefault(tenant_id, []).append(event)
        return event


def _plan_status(tenant_id: str, plan_code: PlanCode) -> PlanStatus:
    if plan_code == PlanCode.SIGNAL_BASIC:
        return PlanStatus(
            tenant_id=tenant_id,
            plan_code=plan_code,
            status=SubscriptionStatus.ACTIVE,
            allowed_modes=(ProductMode.SIGNAL_STATION,),
            automation_enabled=False,
            live_trading_allowed=False,
        )
    if plan_code == PlanCode.AUTOMATION_LIVE:
        return PlanStatus(
            tenant_id=tenant_id,
            plan_code=plan_code,
            status=SubscriptionStatus.ACTIVE,
            allowed_modes=(ProductMode.SIGNAL_STATION, ProductMode.AUTOMATION_STATION),
            automation_enabled=True,
            live_trading_allowed=True,
        )
    return PlanStatus(
        tenant_id=tenant_id,
        plan_code=plan_code,
        status=SubscriptionStatus.ACTIVE,
        allowed_modes=(ProductMode.SIGNAL_STATION, ProductMode.AUTOMATION_STATION),
        automation_enabled=True,
        live_trading_allowed=False,
    )


def signal_detail(summary: SignalSummary) -> SignalDetail:
    return SignalDetail(
        **summary.model_dump(),
        market_context={
            "market_weather": "balanced",
            "headline_context": "fixture provider metadata present",
        },
        data_limitations=("provider data may be delayed or incomplete",),
        risk_disclosure=(
            "Signals are informational. User-directed stocks/options automation can lose money."
        ),
    )


def _redact_details(details: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in details.items():
        if key.lower() in {"token", "api_key", "credential", "account_id", "session"}:
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    return redacted


def _id(prefix: str, *parts: str) -> str:
    digest = sha256(":".join(parts).encode()).hexdigest()
    return f"{prefix}_{digest[:24]}"
