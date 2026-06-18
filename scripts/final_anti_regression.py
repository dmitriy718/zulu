from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from pydantic import ValidationError
from zulu_api import create_app
from zulu_api.security import redact_headers
from zulu_api.settings import Settings
from zulu_contracts import AssetType, BrokerOrderRequest, CleanSignalV1, OrderSide, OrderType
from zulu_execution import (
    BrokerCallPrerequisites,
    KillSwitch,
    KillSwitchRegistry,
    KillSwitchScope,
    LiveBrokerAdapter,
    PaperBrokerAdapter,
    ReconciliationWorker,
)
from zulu_execution.adapters import BrokerAdapterError
from zulu_execution.lifecycle import ExecutionRecord
from zulu_learning import (
    LearningModel,
    ModelEvaluationSummary,
    ModelStatus,
    PromotionGate,
    PromotionGateWorkflow,
)
from zulu_learning.repository import InMemoryLearningRepository
from zulu_observability import build_audit_event
from zulu_observability.metrics import REQUIRED_METRICS
from zulu_policy import (
    PolicyDecision,
)
from zulu_risk import RiskDecision
from zulu_signal_intelligence.constraints import MarketDataQualityError
from zulu_signal_intelligence.fixture_provider import FixtureMarketDataProvider
from zulu_signal_intelligence.ledger import (
    AcceptedSignalCannotBeDeleted,
    InMemorySignalLedgerRepository,
)
from zulu_signal_intelligence.normalizers import normalize_stock_quote
from zulu_signal_intelligence.pipeline import SignalIntelligencePipeline

NOW = datetime(2026, 6, 18, 14, 30, tzinfo=UTC)
TENANT_ID = "tenant_1"
USER_ID = "user_1"


def main() -> None:
    checks = [
        ("accepted signal cannot disappear", check_accepted_signal_cannot_disappear),
        ("broker call requires policy and risk", check_broker_call_requires_gates),
        ("live mode disabled by default", check_live_disabled_by_default),
        ("unsupported assets rejected", check_unsupported_assets_rejected),
        ("options require metadata", check_options_require_metadata),
        ("stop loss required", check_stop_loss_required),
        ("idempotency key required", check_idempotency_key_required),
        ("tenant isolation works", check_tenant_isolation),
        ("secrets are redacted", check_secret_redaction),
        ("model promotion cannot skip gates", check_model_promotion_gates),
        ("kill switches block execution", check_kill_switch_blocks_execution),
        ("provider stale data blocks signals", check_stale_provider_data_blocks),
        ("reconciliation discrepancy creates incident", check_reconciliation_incident),
        ("release metrics are declared", check_release_metrics_declared),
    ]
    for label, check in checks:
        check()
        print(f"PASS {label}")


def clean_signal() -> CleanSignalV1:
    repository = InMemorySignalLedgerRepository()
    result = SignalIntelligencePipeline(
        provider=FixtureMarketDataProvider(now=NOW),
        repository=repository,
    ).run(
        tenant_id=TENANT_ID,
        ticker="MSFT",
        user_id=USER_ID,
        actor_id="release_gate",
        correlation_id="release_gate",
        now=NOW,
    )
    assert result.accepted_signal is not None
    return result.accepted_signal


def check_accepted_signal_cannot_disappear() -> None:
    repository = InMemorySignalLedgerRepository()
    result = SignalIntelligencePipeline(
        provider=FixtureMarketDataProvider(now=NOW),
        repository=repository,
    ).run(
        tenant_id=TENANT_ID,
        ticker="MSFT",
        user_id=USER_ID,
        actor_id="release_gate",
        correlation_id="release_gate",
        now=NOW,
    )
    assert result.accepted_signal is not None
    try:
        repository.delete_signal(result.accepted_signal.signal_id)
    except AcceptedSignalCannotBeDeleted:
        return
    raise AssertionError("accepted signal deletion was allowed")


def check_broker_call_requires_gates() -> None:
    try:
        BrokerCallPrerequisites(
            policy_decision=PolicyDecision(
                approved=False,
                reason="blocked",
                policy_version="policy-v1",
            ),
            risk_decision=RiskDecision(approved=True, reason="risk checks passed"),
            idempotency_key="idem_release_gate_0001",
            audit_event_id="audit_1",
        )
    except ValidationError:
        return
    raise AssertionError("broker prerequisites accepted failed PolicyGate decision")


def check_live_disabled_by_default() -> None:
    assert Settings().live_trading_enabled is False
    try:
        LiveBrokerAdapter().ensure_enabled()
    except BrokerAdapterError:
        return
    raise AssertionError("live adapter enabled by default")


def check_unsupported_assets_rejected() -> None:
    signal = clean_signal()
    data = signal.model_dump()
    data["asset_type"] = "crypto"
    try:
        CleanSignalV1.model_validate(data)
    except ValidationError:
        return
    raise AssertionError("unsupported asset type was accepted")


def check_options_require_metadata() -> None:
    signal = clean_signal()
    data = signal.model_dump()
    data["asset_type"] = AssetType.OPTION
    data["option_contract"] = None
    try:
        CleanSignalV1.model_validate(data)
    except ValidationError:
        return
    raise AssertionError("option signal without contract metadata was accepted")


def check_stop_loss_required() -> None:
    signal = clean_signal()
    data = signal.model_dump()
    data.pop("stop_loss")
    try:
        CleanSignalV1.model_validate(data)
    except ValidationError:
        return
    raise AssertionError("signal without stop loss was accepted")


def check_idempotency_key_required() -> None:
    signal = clean_signal()
    request_data = {
        "broker_order_request_id": "bor_1",
        "tenant_id": signal.tenant_id,
        "execution_intent_id": "intent_1",
        "side": OrderSide.BUY,
        "order_type": OrderType.LIMIT,
        "quantity": Decimal("1"),
        "limit_price": Decimal("1"),
        "created_at": NOW,
    }
    try:
        BrokerOrderRequest.model_validate(request_data)
    except ValidationError:
        return
    raise AssertionError("broker order without idempotency key was accepted")


def check_tenant_isolation() -> None:
    client = TestClient(create_app(Settings()))
    response = client.get(
        "/tenants/tenant_2/signals",
        headers={"Authorization": "Bearer token-owner"},
    )
    assert response.status_code == 404


def check_secret_redaction() -> None:
    event = build_audit_event(
        tenant_id=TENANT_ID,
        actor_id=USER_ID,
        action="credential.check",
        decision="blocked",
        correlation_id="release_gate",
        details={"token": "secret", "reason": "redacted"},
    )
    headers = redact_headers({"authorization": "Bearer secret", "x-request-id": "req_1"})
    assert "token" not in event.details
    assert headers["authorization"] == "[REDACTED]"


def check_model_promotion_gates() -> None:
    decision = PromotionGate().evaluate(
        ModelEvaluationSummary(
            model_id="candidate",
            labeled_outcome_count=500,
            evaluation_window_days=90,
            approved_for_promotion=False,
        )
    )
    assert decision.approved is False
    repository = InMemoryLearningRepository()
    manifest = clean_signal().model_dump()["model_manifest_id"]
    model_manifest = _model_manifest(str(manifest))
    model = LearningModel(
        manifest=model_manifest,
        status=ModelStatus.SHADOW,
        training_window_start=NOW - timedelta(days=90),
        training_window_end=NOW - timedelta(days=1),
        calibration_report="baseline has insufficient calibration for approval",
        allowed_asset_types=frozenset({AssetType.STOCK}),
        allowed_strategy_types=frozenset({"vwap_reclaim"}),
    )
    repository.add_model(model)
    workflow_decision = PromotionGateWorkflow(repository).evaluate_promotion(
        model=model,
        to_status=ModelStatus.APPROVED,
        completed_stages=frozenset(),
        evaluation_report_id="missing",
        risk_review_record_id="risk_review_1",
        rollback_plan="rollback to baseline",
        promoted_by="operator",
        promoted_at=NOW,
    )
    assert workflow_decision.approved is False


def _model_manifest(model_manifest_id: str):
    from zulu_contracts import ModelManifest

    return ModelManifest(
        model_manifest_id=model_manifest_id,
        tenant_id=TENANT_ID,
        model_name="release gate model",
        model_version="0.0.1",
        feature_schema_version="canonical_features_v1",
        artifact_uri="registry://release-gate",
        training_data_hash="f" * 64,
        created_at=NOW,
    )


def check_kill_switch_blocks_execution() -> None:
    signal = clean_signal()
    registry = KillSwitchRegistry(
        switches=(
            KillSwitch(
                scope=KillSwitchScope.TENANT,
                tenant_id=signal.tenant_id,
                reason="release gate tenant halt",
            ),
        )
    )
    reason = registry.first_blocking_reason(
        signal=signal,
        user_id=USER_ID,
        broker_name="paper",
    )
    assert reason == "release gate tenant halt"


def check_stale_provider_data_blocks() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    stale = provider.get_stock_quote("MSFT").model_copy(
        update={"observed_at": NOW - timedelta(minutes=10)}
    )
    try:
        normalize_stock_quote(stale, tenant_id=TENANT_ID, now=NOW)
    except MarketDataQualityError:
        return
    raise AssertionError("stale provider data was accepted")


def check_reconciliation_incident() -> None:
    record = ExecutionRecord(signal=clean_signal())
    _events, incidents = ReconciliationWorker(PaperBrokerAdapter()).reconcile(record, now=NOW)
    assert incidents
    assert incidents[0].status.value == "open"


def check_release_metrics_declared() -> None:
    assert {
        "api.health",
        "api.latency_ms",
        "signals.throughput",
        "policy.blocks",
        "risk.blocks",
        "reconciliation.discrepancies",
        "provider.rate_limits",
        "model.status",
        "incidents.active",
    } <= REQUIRED_METRICS


if __name__ == "__main__":
    main()
