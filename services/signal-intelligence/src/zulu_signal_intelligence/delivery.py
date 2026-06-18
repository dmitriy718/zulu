from __future__ import annotations

from dataclasses import dataclass

from zulu_contracts import AcceptedSignalTerminalState, CleanSignalV1
from zulu_policy import PolicyGate, PolicyInput

from zulu_signal_intelligence.ledger import DurableOutboxPublisher, SignalLedgerRepository


@dataclass(frozen=True)
class DeliveryResult:
    terminal_state: AcceptedSignalTerminalState
    reason: str


class SignalStationDeliveryHandler:
    def __init__(
        self,
        *,
        repository: SignalLedgerRepository,
        outbox: DurableOutboxPublisher,
    ) -> None:
        self.repository = repository
        self.outbox = outbox

    def deliver(
        self, *, signal: CleanSignalV1, actor_id: str, correlation_id: str
    ) -> DeliveryResult:
        self.outbox.publish(
            tenant_id=signal.tenant_id,
            event_type="signal_station.signal_delivered",
            aggregate_type="clean_signal",
            aggregate_id=signal.signal_id,
            idempotency_key=f"signal_station.delivered:{signal.signal_id}",
            payload={
                "signal_id": signal.signal_id,
                "ticker": signal.ticker,
                "asset_type": signal.asset_type.value,
                "confidence_score": str(signal.confidence_score),
                "risk_score": str(signal.risk_score),
            },
            created_at=signal.created_at,
        )
        self.repository.transition_terminal(
            signal_id=signal.signal_id,
            terminal_state=AcceptedSignalTerminalState.DELIVERED_TO_SIGNAL_STATION,
            reason="delivered to Signal Station durable outbox",
            actor_id=actor_id,
            correlation_id=correlation_id,
            occurred_at=signal.created_at,
        )
        return DeliveryResult(
            terminal_state=AcceptedSignalTerminalState.DELIVERED_TO_SIGNAL_STATION,
            reason="delivered to Signal Station durable outbox",
        )


class AutomationStationRoutingHook:
    def __init__(
        self,
        *,
        repository: SignalLedgerRepository,
        outbox: DurableOutboxPublisher,
        policy_gate: PolicyGate | None = None,
    ) -> None:
        self.repository = repository
        self.outbox = outbox
        self.policy_gate = policy_gate or PolicyGate()

    def route_for_policy_review(
        self,
        *,
        signal: CleanSignalV1,
        policy_input: PolicyInput,
        actor_id: str,
        correlation_id: str,
    ) -> DeliveryResult:
        decision = self.policy_gate.evaluate(policy_input)
        event_type = "automation_station.policy_approved_for_risk_review"
        terminal_state = AcceptedSignalTerminalState.DELIVERED_TO_SIGNAL_STATION
        reason = "policy approved for later RiskGate review; no broker execution attempted"
        if not decision.approved:
            event_type = "automation_station.policy_rejected"
            terminal_state = AcceptedSignalTerminalState.POLICY_REJECTED
            reason = decision.reason
        self.outbox.publish(
            tenant_id=signal.tenant_id,
            event_type=event_type,
            aggregate_type="clean_signal",
            aggregate_id=signal.signal_id,
            idempotency_key=f"{event_type}:{signal.signal_id}:{decision.policy_version}",
            payload={
                "signal_id": signal.signal_id,
                "policy_version": decision.policy_version,
                "approved": decision.approved,
                "reason": decision.reason,
                "broker_execution_attempted": False,
            },
            created_at=signal.created_at,
        )
        self.repository.transition_terminal(
            signal_id=signal.signal_id,
            terminal_state=terminal_state,
            reason=reason,
            actor_id=actor_id,
            correlation_id=correlation_id,
            occurred_at=signal.created_at,
        )
        return DeliveryResult(terminal_state=terminal_state, reason=reason)
