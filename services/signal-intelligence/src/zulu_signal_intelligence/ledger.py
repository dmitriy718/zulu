from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Any, Protocol

from zulu_contracts import AcceptedSignalTerminalState, AuditEvent, CleanSignalV1, StrategyCandidate


class AcceptedSignalCannotBeDeleted(RuntimeError):
    pass


class SignalLedgerError(RuntimeError):
    pass


@dataclass(frozen=True)
class OutboxEvent:
    outbox_event_id: str
    tenant_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    idempotency_key: str
    payload: dict[str, Any]
    created_at: datetime
    processed_at: datetime | None = None


@dataclass
class StoredSignalRecord:
    signal: CleanSignalV1
    candidate: StrategyCandidate
    acceptance_status: str
    terminal_state: AcceptedSignalTerminalState | None = None
    terminal_reason: str | None = None


class SignalLedgerRepository(Protocol):
    def persist_accepted(
        self,
        *,
        signal: CleanSignalV1,
        candidate: StrategyCandidate,
        actor_id: str,
        correlation_id: str,
    ) -> None: ...

    def transition_terminal(
        self,
        *,
        signal_id: str,
        terminal_state: AcceptedSignalTerminalState,
        reason: str,
        actor_id: str,
        correlation_id: str,
        occurred_at: datetime,
    ) -> None: ...

    def append_outbox(
        self,
        *,
        tenant_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
        created_at: datetime,
    ) -> OutboxEvent: ...


@dataclass
class InMemorySignalLedgerRepository:
    records: dict[str, StoredSignalRecord] = field(default_factory=dict)
    audit_events: list[AuditEvent] = field(default_factory=list)
    outbox_events: list[OutboxEvent] = field(default_factory=list)

    def persist_accepted(
        self,
        *,
        signal: CleanSignalV1,
        candidate: StrategyCandidate,
        actor_id: str,
        correlation_id: str,
    ) -> None:
        if signal.signal_id in self.records:
            raise SignalLedgerError(f"signal {signal.signal_id} already exists")
        self.records[signal.signal_id] = StoredSignalRecord(
            signal=signal,
            candidate=candidate,
            acceptance_status="accepted",
        )
        self.audit_events.append(
            _audit_event(
                signal=signal,
                actor_id=actor_id,
                action="clean_signal.accepted",
                decision="accepted",
                correlation_id=correlation_id,
                details={
                    "candidate_id": candidate.strategy_candidate_id,
                    "feature_hash": signal.feature_hash,
                    "policy_status": signal.policy_status.value,
                },
            )
        )
        self.append_outbox(
            tenant_id=signal.tenant_id,
            event_type="clean_signal.accepted",
            aggregate_type="clean_signal",
            aggregate_id=signal.signal_id,
            idempotency_key=f"clean_signal.accepted:{signal.signal_id}",
            payload=signal.model_dump(mode="json"),
            created_at=signal.created_at,
        )

    def transition_terminal(
        self,
        *,
        signal_id: str,
        terminal_state: AcceptedSignalTerminalState,
        reason: str,
        actor_id: str,
        correlation_id: str,
        occurred_at: datetime,
    ) -> None:
        record = self.records.get(signal_id)
        if record is None:
            raise SignalLedgerError(f"signal {signal_id} does not exist")
        if record.terminal_state is not None:
            raise SignalLedgerError(f"signal {signal_id} is already terminal")
        record.acceptance_status = "terminal"
        record.terminal_state = terminal_state
        record.terminal_reason = reason
        self.audit_events.append(
            _audit_event(
                signal=record.signal,
                actor_id=actor_id,
                action="clean_signal.terminal_transition",
                decision=terminal_state.value,
                correlation_id=correlation_id,
                details={"reason": reason},
            )
        )
        self.append_outbox(
            tenant_id=record.signal.tenant_id,
            event_type="clean_signal.terminal_transition",
            aggregate_type="clean_signal",
            aggregate_id=record.signal.signal_id,
            idempotency_key=f"clean_signal.terminal:{record.signal.signal_id}:{terminal_state.value}",
            payload={
                "signal_id": record.signal.signal_id,
                "terminal_state": terminal_state.value,
                "reason": reason,
            },
            created_at=occurred_at,
        )

    def append_outbox(
        self,
        *,
        tenant_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
        created_at: datetime,
    ) -> OutboxEvent:
        if any(
            event.tenant_id == tenant_id and event.idempotency_key == idempotency_key
            for event in self.outbox_events
        ):
            raise SignalLedgerError("duplicate outbox idempotency key")
        event = OutboxEvent(
            outbox_event_id=_event_id(tenant_id, event_type, aggregate_id, idempotency_key),
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            idempotency_key=idempotency_key,
            payload=payload,
            created_at=created_at,
        )
        self.outbox_events.append(event)
        return event

    def delete_signal(self, signal_id: str) -> None:
        record = self.records.get(signal_id)
        if record is None:
            return
        if record.acceptance_status in {"accepted", "terminal"}:
            raise AcceptedSignalCannotBeDeleted(
                "accepted signals cannot be deleted; transition to a terminal state instead"
            )
        del self.records[signal_id]


class DurableOutboxPublisher:
    def __init__(self, repository: SignalLedgerRepository) -> None:
        self.repository = repository

    def publish(
        self,
        *,
        tenant_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
        created_at: datetime,
    ) -> OutboxEvent:
        return self.repository.append_outbox(
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            idempotency_key=idempotency_key,
            payload=payload,
            created_at=created_at,
        )


def _audit_event(
    *,
    signal: CleanSignalV1,
    actor_id: str,
    action: str,
    decision: str,
    correlation_id: str,
    details: dict[str, str],
) -> AuditEvent:
    return AuditEvent(
        audit_event_id=_event_id(signal.tenant_id, action, signal.signal_id, decision),
        tenant_id=signal.tenant_id,
        actor_id=actor_id,
        action=action,
        entity_type="clean_signal",
        entity_id=signal.signal_id,
        decision=decision,
        correlation_id=correlation_id,
        occurred_at=signal.created_at,
        details=details,
    )


def _event_id(tenant_id: str, event_type: str, aggregate_id: str, idempotency_key: str) -> str:
    digest = sha256(
        f"{tenant_id}:{event_type}:{aggregate_id}:{idempotency_key}".encode()
    ).hexdigest()
    return f"evt_{digest[:24]}"
