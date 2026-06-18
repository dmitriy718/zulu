from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from zulu_contracts import CleanSignalV1
from zulu_contracts.domain import IncidentSeverity, IncidentStatus, SystemIncident


class KillSwitchScope(StrEnum):
    SYSTEM = "system"
    TENANT = "tenant"
    USER = "user"
    TICKER = "ticker"
    STRATEGY = "strategy"
    MODEL = "model"
    BROKER = "broker"


@dataclass(frozen=True)
class KillSwitch:
    scope: KillSwitchScope
    reason: str
    tenant_id: str | None = None
    user_id: str | None = None
    ticker: str | None = None
    strategy_id: str | None = None
    model_manifest_id: str | None = None
    broker_name: str | None = None
    active: bool = True


class KillSwitchRegistry:
    def __init__(
        self,
        *,
        switches: tuple[KillSwitch, ...] = (),
        active_incidents: tuple[SystemIncident, ...] = (),
    ) -> None:
        self.switches = switches
        self.active_incidents = active_incidents

    def first_blocking_reason(
        self,
        *,
        signal: CleanSignalV1,
        user_id: str,
        broker_name: str,
        strategy_id: str | None = None,
        live_environment: bool = False,
    ) -> str | None:
        if live_environment and any(
            incident.severity == IncidentSeverity.CRITICAL
            and incident.status != IncidentStatus.RESOLVED
            for incident in self.active_incidents
        ):
            return "critical incident blocks live trading"
        for switch in self.switches:
            if not switch.active:
                continue
            if switch.scope == KillSwitchScope.SYSTEM:
                return switch.reason
            if switch.scope == KillSwitchScope.TENANT and switch.tenant_id == signal.tenant_id:
                return switch.reason
            if switch.scope == KillSwitchScope.USER and switch.user_id == user_id:
                return switch.reason
            if switch.scope == KillSwitchScope.TICKER and switch.ticker == signal.ticker:
                return switch.reason
            if switch.scope == KillSwitchScope.STRATEGY and switch.strategy_id == strategy_id:
                return switch.reason
            if (
                switch.scope == KillSwitchScope.MODEL
                and switch.model_manifest_id == signal.model_manifest_id
            ):
                return switch.reason
            if switch.scope == KillSwitchScope.BROKER and switch.broker_name == broker_name:
                return switch.reason
        return None
