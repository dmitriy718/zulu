from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Protocol, overload

from pydantic import BaseModel, ConfigDict, Field, model_validator
from zulu_contracts import (
    BrokerOrderRequest,
    OrderLifecycleEvent,
    OrderLifecycleStatus,
    OrderSide,
)
from zulu_policy import ExecutionEnvironment, PolicyDecision
from zulu_risk import RiskDecision


class BrokerAdapterError(RuntimeError):
    pass


class UnknownBrokerStateError(BrokerAdapterError):
    pass


class BrokerOrderStatus(StrEnum):
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BrokerCallPrerequisites(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    policy_decision: PolicyDecision
    risk_decision: RiskDecision
    idempotency_key: str = Field(min_length=16, max_length=120)
    audit_event_id: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def enforce_gate_approvals(self) -> BrokerCallPrerequisites:
        if not self.policy_decision.approved:
            raise ValueError("broker call requires PolicyGate approval")
        if not self.risk_decision.approved:
            raise ValueError("broker call requires RiskGate approval")
        return self


class OrderSubmission(BaseModel):
    broker_mode: str
    accepted: bool
    idempotency_key: str
    audit_event_id: str
    broker_order_id: str | None = None
    status: BrokerOrderStatus = BrokerOrderStatus.ACCEPTED
    response_metadata: dict[str, str] = Field(default_factory=dict)


@dataclass(frozen=True)
class BrokerOrderResponse:
    broker_mode: str
    broker_order_id: str
    idempotency_key: str
    status: BrokerOrderStatus
    accepted: bool
    response_metadata: Mapping[str, str]
    received_at: datetime


class BrokerAdapter(Protocol):
    broker_mode: str

    def submit_order(
        self,
        request: BrokerOrderRequest,
        prerequisites: BrokerCallPrerequisites,
    ) -> BrokerOrderResponse: ...

    def get_order_status(self, broker_order_id: str) -> BrokerOrderResponse: ...


@dataclass
class PaperBrokerAdapter:
    broker_mode: str = "paper"
    _responses_by_idempotency: dict[str, BrokerOrderResponse] = field(default_factory=dict)
    _responses_by_broker_id: dict[str, BrokerOrderResponse] = field(default_factory=dict)

    @overload
    def submit_order(
        self,
        request_or_prerequisites: BrokerCallPrerequisites,
        prerequisites: None = None,
    ) -> OrderSubmission: ...

    @overload
    def submit_order(
        self,
        request_or_prerequisites: BrokerOrderRequest,
        prerequisites: BrokerCallPrerequisites,
    ) -> BrokerOrderResponse: ...

    def submit_order(
        self,
        request_or_prerequisites: BrokerOrderRequest | BrokerCallPrerequisites,
        prerequisites: BrokerCallPrerequisites | None = None,
    ) -> BrokerOrderResponse | OrderSubmission:
        if prerequisites is None:
            legacy_prerequisites = _coerce_prerequisites(request_or_prerequisites)
            return OrderSubmission(
                broker_mode=self.broker_mode,
                accepted=True,
                idempotency_key=legacy_prerequisites.idempotency_key,
                audit_event_id=legacy_prerequisites.audit_event_id,
                broker_order_id=_broker_order_id(legacy_prerequisites.idempotency_key),
            )
        request = _coerce_request(request_or_prerequisites)
        _validate_broker_request(request)
        if request.idempotency_key != prerequisites.idempotency_key:
            raise BrokerAdapterError("request idempotency key must match broker prerequisites")
        if prerequisites.idempotency_key in self._responses_by_idempotency:
            return self._responses_by_idempotency[prerequisites.idempotency_key]
        response = BrokerOrderResponse(
            broker_mode=self.broker_mode,
            broker_order_id=_broker_order_id(prerequisites.idempotency_key),
            idempotency_key=prerequisites.idempotency_key,
            status=BrokerOrderStatus.ACCEPTED,
            accepted=True,
            response_metadata={
                "adapter": self.broker_mode,
                "client_order_id": prerequisites.idempotency_key,
            },
            received_at=request.created_at,
        )
        self._responses_by_idempotency[prerequisites.idempotency_key] = response
        self._responses_by_broker_id[response.broker_order_id] = response
        return response

    def get_order_status(self, broker_order_id: str) -> BrokerOrderResponse:
        try:
            return self._responses_by_broker_id[broker_order_id]
        except KeyError as exc:
            raise UnknownBrokerStateError("paper broker order is unknown") from exc

    def mark_filled(self, broker_order_id: str, *, filled_at: datetime) -> BrokerOrderResponse:
        return self._replace_status(broker_order_id, BrokerOrderStatus.FILLED, filled_at)

    def mark_partial(self, broker_order_id: str, *, observed_at: datetime) -> BrokerOrderResponse:
        return self._replace_status(broker_order_id, BrokerOrderStatus.PARTIAL, observed_at)

    def mark_cancelled(
        self, broker_order_id: str, *, cancelled_at: datetime
    ) -> BrokerOrderResponse:
        return self._replace_status(broker_order_id, BrokerOrderStatus.CANCELLED, cancelled_at)

    def _replace_status(
        self,
        broker_order_id: str,
        status: BrokerOrderStatus,
        at: datetime,
    ) -> BrokerOrderResponse:
        current = self.get_order_status(broker_order_id)
        updated = BrokerOrderResponse(
            broker_mode=current.broker_mode,
            broker_order_id=current.broker_order_id,
            idempotency_key=current.idempotency_key,
            status=status,
            accepted=current.accepted,
            response_metadata=current.response_metadata,
            received_at=at,
        )
        self._responses_by_broker_id[broker_order_id] = updated
        self._responses_by_idempotency[current.idempotency_key] = updated
        return updated


@dataclass(frozen=True)
class LiveBrokerAdapter:
    broker_mode: str = "live"
    enabled: bool = False
    environment: ExecutionEnvironment = ExecutionEnvironment.PAPER
    live_trading_enabled: bool = False
    credential_ref: str | None = None

    def submit_order(
        self,
        request: BrokerOrderRequest,
        prerequisites: BrokerCallPrerequisites,
    ) -> BrokerOrderResponse:
        self.ensure_enabled()
        _validate_broker_request(request)
        if request.idempotency_key != prerequisites.idempotency_key:
            raise BrokerAdapterError("request idempotency key must match broker prerequisites")
        raise BrokerAdapterError("live broker transport is not configured")

    def get_order_status(self, broker_order_id: str) -> BrokerOrderResponse:
        self.ensure_enabled()
        raise BrokerAdapterError("live broker status transport is not configured")

    def ensure_enabled(self) -> None:
        if not self.enabled:
            raise BrokerAdapterError("live broker adapter is disabled")
        if self.environment != ExecutionEnvironment.LIVE:
            raise BrokerAdapterError("live broker adapter requires live environment")
        if not self.live_trading_enabled:
            raise BrokerAdapterError("live trading is not explicitly enabled")
        if not self.credential_ref:
            raise BrokerAdapterError("live broker adapter requires a credential reference")


def lifecycle_event_from_response(
    *,
    tenant_id: str,
    broker_order_request_id: str,
    response: BrokerOrderResponse,
    occurred_at: datetime,
) -> OrderLifecycleEvent:
    return OrderLifecycleEvent(
        order_lifecycle_event_id=_lifecycle_id(broker_order_request_id, response.status.value),
        tenant_id=tenant_id,
        broker_order_request_id=broker_order_request_id,
        status=_contract_status(response.status),
        occurred_at=occurred_at,
        broker_event_id=response.broker_order_id,
        reconciled_at=occurred_at,
        details={
            "broker_mode": response.broker_mode,
            "idempotency_key": response.idempotency_key,
            "status": response.status.value,
        },
    )


def _contract_status(status: BrokerOrderStatus) -> OrderLifecycleStatus:
    return {
        BrokerOrderStatus.REJECTED: OrderLifecycleStatus.REJECTED,
        BrokerOrderStatus.ACCEPTED: OrderLifecycleStatus.ACKNOWLEDGED,
        BrokerOrderStatus.FILLED: OrderLifecycleStatus.FILLED,
        BrokerOrderStatus.PARTIAL: OrderLifecycleStatus.PARTIALLY_FILLED,
        BrokerOrderStatus.CANCELLED: OrderLifecycleStatus.CANCELLED,
        BrokerOrderStatus.EXPIRED: OrderLifecycleStatus.CANCELLED,
    }[status]


def _validate_broker_request(request: BrokerOrderRequest) -> None:
    if len(request.idempotency_key) < 16:
        raise BrokerAdapterError("broker request requires idempotency key")
    if request.quantity <= Decimal("0"):
        raise BrokerAdapterError("broker request quantity must be positive")
    if request.side not in {OrderSide.BUY, OrderSide.SELL}:
        raise BrokerAdapterError("broker request side is unsupported")


def _coerce_prerequisites(
    value: BrokerOrderRequest | BrokerCallPrerequisites,
) -> BrokerCallPrerequisites:
    if not isinstance(value, BrokerCallPrerequisites):
        raise TypeError("legacy submission requires BrokerCallPrerequisites")
    return value


def _coerce_request(value: BrokerOrderRequest | BrokerCallPrerequisites) -> BrokerOrderRequest:
    if not isinstance(value, BrokerOrderRequest):
        raise TypeError("broker request is required")
    return value


def _broker_order_id(idempotency_key: str) -> str:
    return f"paper_{sha256(idempotency_key.encode()).hexdigest()[:24]}"


def _lifecycle_id(broker_order_request_id: str, status: str) -> str:
    digest = sha256(f"{broker_order_request_id}:{status}".encode()).hexdigest()
    return f"life_{digest[:24]}"
