from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from zulu_contracts import AssetType, CleanSignalV1, OrderLifecycleStatus
from zulu_contracts.domain import IncidentSeverity, IncidentStatus, SystemIncident
from zulu_execution import (
    BrokerAdapterError,
    BrokerCallPrerequisites,
    ExecutionAuthorityResult,
    ExecutionAuthorityService,
    KillSwitch,
    KillSwitchRegistry,
    KillSwitchScope,
    LiveBrokerAdapter,
    PaperBrokerAdapter,
    ReconciliationWorker,
    service_health,
)
from zulu_policy import ExecutionEnvironment, PolicyContext, PolicyDecision, SubscriptionMode
from zulu_risk import RiskContext, RiskDecision, RiskLimits
from zulu_signal_intelligence.fixture_provider import FixtureMarketDataProvider
from zulu_signal_intelligence.ledger import InMemorySignalLedgerRepository
from zulu_signal_intelligence.pipeline import SignalIntelligencePipeline

NOW = datetime(2026, 6, 18, 14, 30, tzinfo=UTC)


def test_execution_health_is_testable() -> None:
    assert service_health().service == "execution"


def test_broker_prerequisites_require_policy_and_risk_approval() -> None:
    with pytest.raises(ValidationError):
        BrokerCallPrerequisites(
            policy_decision=PolicyDecision(
                approved=False,
                reason="missing approval",
                policy_version="policy-1",
            ),
            risk_decision=RiskDecision(approved=True, reason="risk checks passed"),
            idempotency_key="idem_1234567890123456",
            audit_event_id="audit_1",
        )


def test_paper_adapter_requires_prerequisites_before_submission() -> None:
    prerequisites = BrokerCallPrerequisites(
        policy_decision=PolicyDecision(
            approved=True,
            reason="policy checks passed",
            policy_version="policy-1",
        ),
        risk_decision=RiskDecision(approved=True, reason="risk checks passed"),
        idempotency_key="idem_1234567890123456",
        audit_event_id="audit_1",
    )

    submission = PaperBrokerAdapter().submit_order(prerequisites)

    assert submission.accepted is True
    assert submission.broker_mode == "paper"


def _clean_signal(asset_type: AssetType = AssetType.STOCK) -> CleanSignalV1:
    result = SignalIntelligencePipeline(
        provider=FixtureMarketDataProvider(now=NOW),
        repository=InMemorySignalLedgerRepository(),
    ).run(
        tenant_id="tenant_1",
        ticker="MSFT",
        option_symbol="MSFT270117C00100000" if asset_type == AssetType.OPTION else None,
        user_id="user_1",
        actor_id="execution_test",
        correlation_id="execution_test",
        now=NOW,
    )
    assert result.accepted_signal is not None
    return result.accepted_signal


def _policy_context() -> PolicyContext:
    return PolicyContext(
        tenant_id="tenant_1",
        user_id="user_1",
        user_approved_signal=True,
        instrument_allowed=True,
        policy_version="policy-execution-v1",
        subscription_mode=SubscriptionMode.PAPER_AUTOMATION,
        user_automation_permission=True,
        environment=ExecutionEnvironment.PAPER,
        supported_asset_types=frozenset({AssetType.STOCK, AssetType.OPTION}),
        now=NOW,
    )


def _risk_context() -> RiskContext:
    return RiskContext(
        tenant_id="tenant_1",
        user_id="user_1",
        now=NOW,
        order_notional=Decimal("1000"),
        estimated_max_loss=Decimal("100"),
        requested_quantity=Decimal("1"),
    )


def _risk_limits() -> RiskLimits:
    return RiskLimits(max_order_notional=Decimal("10000"), max_symbol_exposure=Decimal("25000"))


def _execute_with_paper(
    idempotency_key: str,
) -> tuple[ExecutionAuthorityService, ExecutionAuthorityResult]:
    service = ExecutionAuthorityService(broker_adapter=PaperBrokerAdapter())
    result = service.execute_signal(
        signal=_clean_signal(),
        policy_context=_policy_context(),
        risk_context=_risk_context(),
        risk_limits=_risk_limits(),
        user_id="user_1",
        actor_id="execution_test",
        correlation_id="corr_1",
        idempotency_key=idempotency_key,
        quantity=Decimal("1"),
        now=NOW,
    )
    return service, result


def test_execution_authority_approves_paper_order_and_lifecycle() -> None:
    _service, result = _execute_with_paper("idem_execution_0001")

    assert result.approved is True
    assert result.record.execution_intent is not None
    assert result.record.broker_order_request is not None
    assert result.record.lifecycle_events[-1].status == OrderLifecycleStatus.ACKNOWLEDGED
    assert len(result.record.audit_events) >= 4


def test_execution_authority_blocks_without_policy_approval_before_broker_call() -> None:
    service = ExecutionAuthorityService(broker_adapter=PaperBrokerAdapter())
    policy_context = _policy_context().model_copy(update={"user_approved_signal": False})

    result = service.execute_signal(
        signal=_clean_signal(),
        policy_context=policy_context,
        risk_context=_risk_context(),
        risk_limits=_risk_limits(),
        user_id="user_1",
        actor_id="execution_test",
        correlation_id="corr_1",
        idempotency_key="idem_execution_0002",
        quantity=Decimal("1"),
        now=NOW,
    )

    assert result.approved is False
    assert "approval" in result.reason
    assert result.record.broker_order_request is None


def test_execution_authority_blocks_without_risk_approval_before_broker_call() -> None:
    service = ExecutionAuthorityService(broker_adapter=PaperBrokerAdapter())
    risk_context = _risk_context().model_copy(update={"estimated_max_loss": Decimal("2000")})

    result = service.execute_signal(
        signal=_clean_signal(),
        policy_context=_policy_context(),
        risk_context=risk_context,
        risk_limits=_risk_limits().model_copy(update={"max_risk_per_trade": Decimal("100")}),
        user_id="user_1",
        actor_id="execution_test",
        correlation_id="corr_1",
        idempotency_key="idem_execution_0003",
        quantity=Decimal("1"),
        now=NOW,
    )

    assert result.approved is False
    assert "risk per trade" in result.reason
    assert result.record.broker_order_request is None


def test_paper_broker_idempotency_returns_same_response() -> None:
    service, result = _execute_with_paper("idem_execution_0004")
    adapter = service.broker_adapter
    assert result.record.broker_order_request is not None
    prerequisites = BrokerCallPrerequisites(
        policy_decision=PolicyDecision(
            approved=True,
            reason="policy checks passed",
            policy_version="policy-execution-v1",
        ),
        risk_decision=RiskDecision(approved=True, reason="risk checks passed"),
        idempotency_key="idem_execution_0004",
        audit_event_id="audit_1",
    )

    first = adapter.submit_order(result.record.broker_order_request, prerequisites)
    second = adapter.submit_order(result.record.broker_order_request, prerequisites)

    assert first == second


def test_live_broker_adapter_is_hard_gated() -> None:
    _service, result = _execute_with_paper("idem_execution_0005")
    assert result.record.broker_order_request is not None
    prerequisites = BrokerCallPrerequisites(
        policy_decision=PolicyDecision(
            approved=True,
            reason="policy checks passed",
            policy_version="policy-execution-v1",
        ),
        risk_decision=RiskDecision(approved=True, reason="risk checks passed"),
        idempotency_key="idem_execution_0005",
        audit_event_id="audit_1",
    )

    with pytest.raises(BrokerAdapterError, match="disabled"):
        LiveBrokerAdapter().submit_order(result.record.broker_order_request, prerequisites)


def test_reconciliation_records_fill_from_paper_broker() -> None:
    service, result = _execute_with_paper("idem_execution_0006")
    adapter = service.broker_adapter
    assert isinstance(adapter, PaperBrokerAdapter)
    assert result.record.broker_order_id is not None
    adapter.mark_filled(result.record.broker_order_id, filled_at=NOW + timedelta(seconds=10))

    events, incidents = ReconciliationWorker(adapter).reconcile(
        result.record,
        now=NOW + timedelta(seconds=10),
    )

    assert incidents == []
    assert events[-1].status == OrderLifecycleStatus.FILLED


def test_reconciliation_emits_incident_for_missing_broker_order() -> None:
    _service, result = _execute_with_paper("idem_execution_0007")
    result.record.broker_order_id = "missing_broker_order"

    events, incidents = ReconciliationWorker(PaperBrokerAdapter()).reconcile(result.record, now=NOW)

    assert events[-1].status == OrderLifecycleStatus.UNRESOLVED
    assert incidents[-1].summary == "broker order status is unavailable"


def test_manual_operator_reconciliation_path() -> None:
    service, result = _execute_with_paper("idem_execution_0008")

    event = ReconciliationWorker(service.broker_adapter).manual_reconcile(
        result.record,
        status=OrderLifecycleStatus.CANCELLED,
        operator_id="operator_1",
        reason="manual cancellation verified",
        now=NOW,
    )

    assert event.status == OrderLifecycleStatus.CANCELLED
    assert event.details["operator_id"] == "operator_1"


def test_kill_switch_blocks_execution_before_broker_call() -> None:
    service = ExecutionAuthorityService(
        broker_adapter=PaperBrokerAdapter(),
        kill_switches=KillSwitchRegistry(
            switches=(
                KillSwitch(
                    scope=KillSwitchScope.TICKER,
                    ticker="MSFT",
                    reason="ticker paused by operator",
                ),
            )
        ),
    )

    result = service.execute_signal(
        signal=_clean_signal(),
        policy_context=_policy_context(),
        risk_context=_risk_context(),
        risk_limits=_risk_limits(),
        user_id="user_1",
        actor_id="execution_test",
        correlation_id="corr_1",
        idempotency_key="idem_execution_0009",
        quantity=Decimal("1"),
        now=NOW,
    )

    assert result.approved is False
    assert "ticker paused" in result.reason
    assert result.record.broker_order_request is None


def test_critical_incident_blocks_live_trading() -> None:
    service = ExecutionAuthorityService(
        broker_adapter=PaperBrokerAdapter(),
        kill_switches=KillSwitchRegistry(
            active_incidents=(
                SystemIncident(
                    system_incident_id="incident_critical",
                    tenant_id="tenant_1",
                    severity=IncidentSeverity.CRITICAL,
                    status=IncidentStatus.OPEN,
                    summary="critical execution incident",
                    opened_at=NOW,
                ),
            )
        ),
    )
    policy_context = _policy_context().model_copy(
        update={
            "environment": ExecutionEnvironment.LIVE,
            "subscription_mode": SubscriptionMode.LIVE_AUTOMATION,
            "live_trading_enabled": True,
        }
    )

    result = service.execute_signal(
        signal=_clean_signal(),
        policy_context=policy_context,
        risk_context=_risk_context().model_copy(update={"live_environment": True}),
        risk_limits=_risk_limits().model_copy(update={"live_trading_enabled": True}),
        user_id="user_1",
        actor_id="execution_test",
        correlation_id="corr_1",
        idempotency_key="idem_execution_0010",
        quantity=Decimal("1"),
        now=NOW,
    )

    assert result.approved is False
    assert "critical incident" in result.reason
