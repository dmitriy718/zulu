from zulu_observability import build_audit_event
from zulu_observability.metrics import REQUIRED_METRICS, ZuluMetrics


def test_audit_event_removes_sensitive_details() -> None:
    event = build_audit_event(
        tenant_id="tenant_1",
        actor_id="user_1",
        action="broker_call_requested",
        decision="rejected",
        correlation_id="corr_1",
        details={"token": "secret", "reason": "missing risk approval"},
    )

    assert "token" not in event.details
    assert event.details["reason"] == "missing risk approval"


def test_required_release_candidate_metrics_are_declared_and_redacted() -> None:
    metrics = ZuluMetrics()
    sample = metrics.record("broker.errors", 1, tenant_id="tenant_1", token="secret")

    assert "broker.errors" in REQUIRED_METRICS
    assert "signals.throughput" in REQUIRED_METRICS
    assert "token" not in sample.labels
