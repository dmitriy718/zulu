import pytest
from pydantic import ValidationError
from zulu_contracts import AssetClass, SignalCandidate, SignalDisposition, SignalStatus


def test_signal_candidate_allows_only_stock_and_option_assets() -> None:
    candidate = SignalCandidate(
        symbol="AAPL",
        asset_class=AssetClass.STOCK,
        thesis="A sufficiently detailed thesis for a stock signal candidate.",
        source="unit-test-fixture",
        confidence_score=0.42,
    )

    assert candidate.asset_class is AssetClass.STOCK


def test_rejected_signal_requires_reason() -> None:
    with pytest.raises(ValidationError):
        SignalDisposition(signal_id="sig_1", status=SignalStatus.REJECTED)


def test_execution_attempt_requires_idempotency_and_audit() -> None:
    with pytest.raises(ValidationError):
        SignalDisposition(signal_id="sig_1", status=SignalStatus.EXECUTION_ATTEMPTED)

    disposition = SignalDisposition(
        signal_id="sig_1",
        status=SignalStatus.EXECUTION_ATTEMPTED,
        idempotency_key="idem_1234567890123456",
        audit_event_id="audit_1",
    )
    assert disposition.audit_event_id == "audit_1"
