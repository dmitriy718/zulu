from zulu_execution import BrokerCallPrerequisites
from zulu_policy import PolicyDecision
from zulu_risk import RiskDecision


def test_broker_call_contract_requires_idempotency_and_audit_event() -> None:
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

    assert prerequisites.idempotency_key.startswith("idem_")
    assert prerequisites.audit_event_id == "audit_1"
