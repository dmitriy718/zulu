from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256

from zulu_contracts import (
    AcceptedSignalTerminalState,
    AuditEvent,
    BrokerOrderRequest,
    CleanSignalV1,
    ExecutionIntent,
    OrderLifecycleEvent,
    OrderLifecycleStatus,
    OrderSide,
    OrderType,
)
from zulu_contracts.domain import (
    DecisionStatus,
    IncidentSeverity,
    IncidentStatus,
    SystemIncident,
)
from zulu_contracts.domain import (
    PolicyDecision as ContractPolicyDecision,
)
from zulu_contracts.domain import (
    RiskDecision as ContractRiskDecision,
)
from zulu_policy import PolicyContext, PolicyDecision, PolicyGate
from zulu_risk import RiskContext, RiskDecision, RiskGate, RiskLimits

from zulu_execution.adapters import (
    BrokerAdapter,
    BrokerCallPrerequisites,
    BrokerOrderResponse,
    PaperBrokerAdapter,
    lifecycle_event_from_response,
)
from zulu_execution.kill_switch import KillSwitchRegistry


class ExecutionAuthorityError(RuntimeError):
    pass


@dataclass
class ExecutionRecord:
    signal: CleanSignalV1
    policy_decision: ContractPolicyDecision | None = None
    risk_decision: ContractRiskDecision | None = None
    execution_intent: ExecutionIntent | None = None
    broker_order_request: BrokerOrderRequest | None = None
    lifecycle_events: list[OrderLifecycleEvent] = field(default_factory=list)
    audit_events: list[AuditEvent] = field(default_factory=list)
    incidents: list[SystemIncident] = field(default_factory=list)
    broker_order_id: str | None = None


@dataclass
class ExecutionAuthorityResult:
    approved: bool
    reason: str
    record: ExecutionRecord


@dataclass
class ExecutionAuthorityService:
    broker_adapter: BrokerAdapter = field(default_factory=PaperBrokerAdapter)
    policy_gate: PolicyGate = field(default_factory=PolicyGate)
    risk_gate: RiskGate = field(default_factory=RiskGate)
    kill_switches: KillSwitchRegistry = field(default_factory=KillSwitchRegistry)
    records_by_signal: dict[str, ExecutionRecord] = field(default_factory=dict)
    idempotency_keys: set[str] = field(default_factory=set)

    def execute_signal(
        self,
        *,
        signal: CleanSignalV1,
        policy_context: PolicyContext,
        risk_context: RiskContext,
        risk_limits: RiskLimits,
        user_id: str,
        actor_id: str,
        correlation_id: str,
        idempotency_key: str,
        quantity: Decimal,
        broker_name: str = "paper",
        strategy_id: str | None = None,
        now: datetime | None = None,
    ) -> ExecutionAuthorityResult:
        requested_at = now or datetime.now(UTC)
        record = self.records_by_signal.setdefault(signal.signal_id, ExecutionRecord(signal=signal))
        kill_reason = self.kill_switches.first_blocking_reason(
            signal=signal,
            user_id=user_id,
            broker_name=broker_name,
            strategy_id=strategy_id,
            live_environment=policy_context.environment.value == "live",
        )
        if kill_reason is not None:
            return self._blocked(
                record, actor_id, correlation_id, "kill_switch", kill_reason, requested_at
            )

        package_policy_decision = self.policy_gate.evaluate(policy_context, signal)
        record.policy_decision = _contract_policy_decision(
            signal=signal,
            decision=package_policy_decision,
            decided_at=requested_at,
        )
        record.audit_events.append(
            _audit_event(
                signal=signal,
                actor_id=actor_id,
                action="policy_gate.evaluated",
                decision="approved" if package_policy_decision.approved else "rejected",
                correlation_id=correlation_id,
                occurred_at=requested_at,
                details={"reason": package_policy_decision.reason},
            )
        )
        if not package_policy_decision.approved:
            return ExecutionAuthorityResult(
                approved=False,
                reason=package_policy_decision.reason,
                record=record,
            )

        package_risk_decision = self.risk_gate.evaluate_signal(signal, risk_context, risk_limits)
        record.risk_decision = _contract_risk_decision(
            signal=signal,
            decision=package_risk_decision,
            decided_at=requested_at,
        )
        record.audit_events.append(
            _audit_event(
                signal=signal,
                actor_id=actor_id,
                action="risk_gate.evaluated",
                decision="approved" if package_risk_decision.approved else "rejected",
                correlation_id=correlation_id,
                occurred_at=requested_at,
                details={"reason": package_risk_decision.reason},
            )
        )
        if not package_risk_decision.approved:
            return ExecutionAuthorityResult(
                approved=False,
                reason=package_risk_decision.reason,
                record=record,
            )
        if idempotency_key in self.idempotency_keys:
            return ExecutionAuthorityResult(
                approved=False,
                reason="duplicate idempotency key",
                record=record,
            )

        execution_intent = ExecutionIntent(
            execution_intent_id=_id("intent", signal.signal_id, idempotency_key),
            tenant_id=signal.tenant_id,
            signal_id=signal.signal_id,
            policy_decision_id=record.policy_decision.policy_decision_id,
            risk_decision_id=record.risk_decision.risk_decision_id,
            terminal_state=AcceptedSignalTerminalState.EXECUTION_ATTEMPTED,
            requested_at=requested_at,
        )
        request = BrokerOrderRequest(
            broker_order_request_id=_id("broker_req", signal.signal_id, idempotency_key),
            tenant_id=signal.tenant_id,
            execution_intent_id=execution_intent.execution_intent_id,
            idempotency_key=idempotency_key,
            side=OrderSide.BUY if signal.direction.value == "long" else OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            limit_price=signal.entry_zone.upper
            if signal.direction.value == "long"
            else signal.entry_zone.lower,
            created_at=requested_at,
        )
        _validate_options_metadata(signal)
        prerequisites = BrokerCallPrerequisites(
            policy_decision=package_policy_decision,
            risk_decision=package_risk_decision,
            idempotency_key=idempotency_key,
            audit_event_id=_id("audit", signal.signal_id, "broker_call", idempotency_key),
        )
        record.audit_events.append(
            _audit_event(
                signal=signal,
                actor_id=actor_id,
                action="broker_order_request.created",
                decision="approved",
                correlation_id=correlation_id,
                occurred_at=requested_at,
                details={"idempotency_key": idempotency_key},
            )
        )
        response = self.broker_adapter.submit_order(request, prerequisites)
        if not isinstance(response, BrokerOrderResponse):
            raise ExecutionAuthorityError(
                "broker adapter returned legacy response in authority flow"
            )
        lifecycle = lifecycle_event_from_response(
            tenant_id=signal.tenant_id,
            broker_order_request_id=request.broker_order_request_id,
            response=response,
            occurred_at=response.received_at,
        )
        self.idempotency_keys.add(idempotency_key)
        record.execution_intent = execution_intent
        record.broker_order_request = request
        record.broker_order_id = response.broker_order_id
        record.lifecycle_events.append(lifecycle)
        record.audit_events.append(
            _audit_event(
                signal=signal,
                actor_id=actor_id,
                action="broker_adapter.response",
                decision=response.status.value,
                correlation_id=correlation_id,
                occurred_at=response.received_at,
                details={"broker_mode": response.broker_mode},
            )
        )
        return ExecutionAuthorityResult(
            approved=True,
            reason="paper order submitted through execution authority",
            record=record,
        )

    def _blocked(
        self,
        record: ExecutionRecord,
        actor_id: str,
        correlation_id: str,
        action: str,
        reason: str,
        occurred_at: datetime,
    ) -> ExecutionAuthorityResult:
        record.audit_events.append(
            _audit_event(
                signal=record.signal,
                actor_id=actor_id,
                action=action,
                decision="blocked",
                correlation_id=correlation_id,
                occurred_at=occurred_at,
                details={"reason": reason},
            )
        )
        return ExecutionAuthorityResult(approved=False, reason=reason, record=record)


class ReconciliationWorker:
    def __init__(self, broker_adapter: BrokerAdapter) -> None:
        self.broker_adapter = broker_adapter

    def reconcile(
        self, record: ExecutionRecord, *, now: datetime
    ) -> tuple[list[OrderLifecycleEvent], list[SystemIncident]]:
        if record.broker_order_request is None or record.broker_order_id is None:
            incident = _incident(
                record.signal.tenant_id, "execution record is missing broker request", now
            )
            record.incidents.append(incident)
            return ([], [incident])
        try:
            broker_response = self.broker_adapter.get_order_status(record.broker_order_id)
        except Exception:
            incident = _incident(record.signal.tenant_id, "broker order status is unavailable", now)
            unresolved = OrderLifecycleEvent(
                order_lifecycle_event_id=_id(
                    "life", record.broker_order_request.broker_order_request_id, "unresolved"
                ),
                tenant_id=record.signal.tenant_id,
                broker_order_request_id=record.broker_order_request.broker_order_request_id,
                status=OrderLifecycleStatus.UNRESOLVED,
                occurred_at=now,
                system_incident_id=incident.system_incident_id,
                details={"reason": "broker order status is unavailable"},
            )
            record.lifecycle_events.append(unresolved)
            record.incidents.append(incident)
            return ([unresolved], [incident])
        event = lifecycle_event_from_response(
            tenant_id=record.signal.tenant_id,
            broker_order_request_id=record.broker_order_request.broker_order_request_id,
            response=broker_response,
            occurred_at=now,
        )
        new_events: list[OrderLifecycleEvent] = []
        if not any(existing.status == event.status for existing in record.lifecycle_events):
            record.lifecycle_events.append(event)
            new_events.append(event)
        incidents: list[SystemIncident] = []
        if _has_duplicate_terminal_events(record.lifecycle_events):
            incidents.append(
                _incident(
                    record.signal.tenant_id, "duplicate terminal fill/cancel events detected", now
                )
            )
        if _has_stale_pending(record.lifecycle_events, now=now):
            incidents.append(
                _incident(record.signal.tenant_id, "stale pending broker order detected", now)
            )
        record.incidents.extend(incidents)
        return (new_events, incidents)

    def manual_reconcile(
        self,
        record: ExecutionRecord,
        *,
        status: OrderLifecycleStatus,
        operator_id: str,
        reason: str,
        now: datetime,
    ) -> OrderLifecycleEvent:
        if record.broker_order_request is None:
            raise ExecutionAuthorityError("manual reconciliation requires broker order request")
        event = OrderLifecycleEvent(
            order_lifecycle_event_id=_id(
                "manual_life", record.broker_order_request.broker_order_request_id, status.value
            ),
            tenant_id=record.signal.tenant_id,
            broker_order_request_id=record.broker_order_request.broker_order_request_id,
            status=status,
            occurred_at=now,
            reconciled_at=now,
            details={"operator_id": operator_id, "reason": reason},
        )
        record.lifecycle_events.append(event)
        return event


def _contract_policy_decision(
    *,
    signal: CleanSignalV1,
    decision: PolicyDecision,
    decided_at: datetime,
) -> ContractPolicyDecision:
    return ContractPolicyDecision(
        policy_decision_id=_id("policy_decision", signal.signal_id, decision.policy_version),
        tenant_id=signal.tenant_id,
        signal_id=signal.signal_id,
        status=DecisionStatus.APPROVED if decision.approved else DecisionStatus.REJECTED,
        reason=str(decision.reason),
        policy_version=str(decision.policy_version),
        decided_at=decided_at,
    )


def _contract_risk_decision(
    *,
    signal: CleanSignalV1,
    decision: RiskDecision,
    decided_at: datetime,
) -> ContractRiskDecision:
    return ContractRiskDecision(
        risk_decision_id=_id("risk_decision", signal.signal_id, decision.risk_version),
        tenant_id=signal.tenant_id,
        signal_id=signal.signal_id,
        status=DecisionStatus.APPROVED if decision.approved else DecisionStatus.REJECTED,
        reason=str(decision.reason),
        risk_version=str(decision.risk_version),
        max_loss=decision.max_loss,
        decided_at=decided_at,
    )


def _validate_options_metadata(signal: CleanSignalV1) -> None:
    if signal.asset_type.value == "option" and signal.option_contract is None:
        raise ExecutionAuthorityError(
            "options execution requires validated option contract metadata"
        )


def _audit_event(
    *,
    signal: CleanSignalV1,
    actor_id: str,
    action: str,
    decision: str,
    correlation_id: str,
    occurred_at: datetime,
    details: dict[str, str],
) -> AuditEvent:
    return AuditEvent(
        audit_event_id=_id("audit", signal.signal_id, action, decision, occurred_at.isoformat()),
        tenant_id=signal.tenant_id,
        actor_id=actor_id,
        action=action,
        entity_type="clean_signal",
        entity_id=signal.signal_id,
        decision=decision,
        correlation_id=correlation_id,
        occurred_at=occurred_at,
        details=details,
    )


def _incident(tenant_id: str, summary: str, opened_at: datetime) -> SystemIncident:
    return SystemIncident(
        system_incident_id=_id("incident", tenant_id, summary, opened_at.isoformat()),
        tenant_id=tenant_id,
        severity=IncidentSeverity.HIGH,
        status=IncidentStatus.OPEN,
        summary=summary,
        opened_at=opened_at,
    )


def _has_duplicate_terminal_events(events: list[OrderLifecycleEvent]) -> bool:
    terminal_count = sum(
        event.status
        in {
            OrderLifecycleStatus.FILLED,
            OrderLifecycleStatus.CANCELLED,
            OrderLifecycleStatus.REJECTED,
        }
        for event in events
    )
    return terminal_count > 1


def _has_stale_pending(events: list[OrderLifecycleEvent], *, now: datetime) -> bool:
    if any(
        event.status
        in {
            OrderLifecycleStatus.FILLED,
            OrderLifecycleStatus.CANCELLED,
            OrderLifecycleStatus.REJECTED,
        }
        for event in events
    ):
        return False
    first = min((event.occurred_at for event in events), default=now)
    return now - first > timedelta(minutes=30)


def _id(prefix: str, *parts: str) -> str:
    digest = sha256(":".join(parts).encode()).hexdigest()
    return f"{prefix}_{digest[:24]}"
