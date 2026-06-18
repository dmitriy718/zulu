from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from zulu_contracts import AcceptedSignalTerminalState, SignalDirection, TakeProfitLevel
from zulu_policy import PolicyInput
from zulu_signal_intelligence.fixture_provider import FixtureMarketDataProvider
from zulu_signal_intelligence.ledger import (
    AcceptedSignalCannotBeDeleted,
    InMemorySignalLedgerRepository,
    SignalLedgerError,
)
from zulu_signal_intelligence.pipeline import SignalIntelligencePipeline
from zulu_signal_intelligence.quality import SignalQualityGate
from zulu_signal_intelligence.scoring import BaselineCandidateScorer
from zulu_signal_intelligence.strategies import (
    OptionsUnusualActivityStrategy,
    StrategyContext,
    VwapReclaimRejectStrategy,
)

NOW = datetime(2026, 6, 18, 14, 30, tzinfo=UTC)
TENANT_ID = "tenant_demo"
USER_ID = "user_demo"
ACTOR_ID = "system_signal_intelligence"
CORRELATION_ID = "corr_signal_pipeline_fixture"
TICKER = "MSFT"
OPTION_SYMBOL = "MSFT270117C00100000"


def test_vwap_strategy_generates_deterministic_candidate_from_fixture_context() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    repository = InMemorySignalLedgerRepository()
    pipeline = SignalIntelligencePipeline(provider=provider, repository=repository)
    context = pipeline.context_service.build_context(tenant_id=TENANT_ID, ticker=TICKER, now=NOW)

    candidate = VwapReclaimRejectStrategy().generate(
        StrategyContext(
            tenant_id=TENANT_ID,
            ticker=TICKER,
            feature_vector=context.feature_vector,
            generated_at=NOW,
        )
    )

    assert candidate is not None
    assert candidate.direction == SignalDirection.LONG
    assert candidate.strategy_candidate_id.startswith("candidate_")


def test_baseline_scorer_marks_model_mode_and_keeps_confidence_separate_from_risk() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    repository = InMemorySignalLedgerRepository()
    pipeline = SignalIntelligencePipeline(provider=provider, repository=repository)
    context = pipeline.context_service.build_context(tenant_id=TENANT_ID, ticker=TICKER, now=NOW)
    candidate = VwapReclaimRejectStrategy().generate(
        StrategyContext(
            tenant_id=TENANT_ID,
            ticker=TICKER,
            feature_vector=context.feature_vector,
            generated_at=NOW,
        )
    )
    assert candidate is not None

    score = BaselineCandidateScorer().score(candidate)

    assert score.model_mode == "baseline"
    assert score.model_manifest_id == "baseline_signal_scorer_v1"
    assert score.confidence_score != score.risk_score
    assert {component.name for component in score.components} >= {
        "trend_alignment",
        "spread_risk",
    }


def test_pipeline_persists_clean_signal_delivers_to_signal_station_and_writes_outbox() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    repository = InMemorySignalLedgerRepository()
    result = SignalIntelligencePipeline(provider=provider, repository=repository).run(
        tenant_id=TENANT_ID,
        ticker=TICKER,
        user_id=USER_ID,
        actor_id=ACTOR_ID,
        correlation_id=CORRELATION_ID,
        now=NOW,
    )

    assert result.accepted_signal is not None
    assert result.terminal_state == AcceptedSignalTerminalState.DELIVERED_TO_SIGNAL_STATION
    stored = repository.records[result.accepted_signal.signal_id]
    assert stored.acceptance_status == "terminal"
    assert stored.terminal_state == AcceptedSignalTerminalState.DELIVERED_TO_SIGNAL_STATION
    assert len(repository.audit_events) == 2
    assert [event.event_type for event in repository.outbox_events] == [
        "clean_signal.accepted",
        "signal_station.signal_delivered",
        "clean_signal.terminal_transition",
    ]


def test_pipeline_can_create_options_signal_when_options_data_supports_it() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    repository = InMemorySignalLedgerRepository()
    result = SignalIntelligencePipeline(
        provider=provider,
        repository=repository,
        strategies=(OptionsUnusualActivityStrategy(),),
    ).run(
        tenant_id=TENANT_ID,
        ticker=TICKER,
        option_symbol=OPTION_SYMBOL,
        user_id=USER_ID,
        actor_id=ACTOR_ID,
        correlation_id=CORRELATION_ID,
        now=NOW,
    )

    assert result.accepted_signal is not None
    assert result.accepted_signal.asset_type.value == "option"
    assert result.accepted_signal.option_contract is not None
    assert result.accepted_signal.option_contract.open_interest > 0


def test_automation_route_calls_policy_gate_and_never_attempts_broker_execution() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    repository = InMemorySignalLedgerRepository()
    result = SignalIntelligencePipeline(provider=provider, repository=repository).run(
        tenant_id=TENANT_ID,
        ticker=TICKER,
        user_id=USER_ID,
        actor_id=ACTOR_ID,
        correlation_id=CORRELATION_ID,
        now=NOW,
        route_to_automation=True,
        policy_input=PolicyInput(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            user_approved_signal=False,
            instrument_allowed=True,
            policy_version="policy-test-v1",
        ),
    )

    assert result.accepted_signal is not None
    assert result.terminal_state == AcceptedSignalTerminalState.POLICY_REJECTED
    policy_outbox = [
        event
        for event in repository.outbox_events
        if event.event_type == "automation_station.policy_rejected"
    ][0]
    assert policy_outbox.payload["broker_execution_attempted"] is False
    assert "approval" in policy_outbox.payload["reason"]


def test_accepted_signal_cannot_disappear_silently_after_acceptance() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    repository = InMemorySignalLedgerRepository()
    result = SignalIntelligencePipeline(provider=provider, repository=repository).run(
        tenant_id=TENANT_ID,
        ticker=TICKER,
        user_id=USER_ID,
        actor_id=ACTOR_ID,
        correlation_id=CORRELATION_ID,
        now=NOW,
    )
    assert result.accepted_signal is not None

    with pytest.raises(AcceptedSignalCannotBeDeleted):
        repository.delete_signal(result.accepted_signal.signal_id)


def test_quality_gate_rejects_nonsensical_risk_reward() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    repository = InMemorySignalLedgerRepository()
    result = SignalIntelligencePipeline(provider=provider, repository=repository).run(
        tenant_id=TENANT_ID,
        ticker=TICKER,
        user_id=USER_ID,
        actor_id=ACTOR_ID,
        correlation_id=CORRELATION_ID,
        now=NOW,
    )
    assert result.accepted_signal is not None
    broken_signal = result.accepted_signal.model_copy(
        update={
            "take_profit_levels": [
                TakeProfitLevel(
                    label="bad",
                    price=Decimal("100.160000"),
                    scale_out_fraction=Decimal("1.000000"),
                )
            ]
        }
    )

    gate_result = SignalQualityGate().evaluate(broken_signal, now=NOW)

    assert gate_result.passed is False
    assert "nonsensical risk/reward" in gate_result.reasons


def test_quality_gate_rejects_expired_signal_timestamp() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    repository = InMemorySignalLedgerRepository()
    result = SignalIntelligencePipeline(provider=provider, repository=repository).run(
        tenant_id=TENANT_ID,
        ticker=TICKER,
        user_id=USER_ID,
        actor_id=ACTOR_ID,
        correlation_id=CORRELATION_ID,
        now=NOW,
    )
    assert result.accepted_signal is not None

    gate_result = SignalQualityGate().evaluate(
        result.accepted_signal,
        now=NOW + timedelta(minutes=1),
    )

    assert gate_result.passed is False
    assert "stale market data" in gate_result.reasons
    assert "expired signal timestamp" in gate_result.reasons


def test_explanation_snapshot_contains_required_sections() -> None:
    provider = FixtureMarketDataProvider(now=NOW)
    repository = InMemorySignalLedgerRepository()
    result = SignalIntelligencePipeline(provider=provider, repository=repository).run(
        tenant_id=TENANT_ID,
        ticker=TICKER,
        user_id=USER_ID,
        actor_id=ACTOR_ID,
        correlation_id=CORRELATION_ID,
        now=NOW,
    )
    assert result.accepted_signal is not None
    signal = result.accepted_signal

    assert signal.technical_context.startswith("What got attention:")
    assert "Setup type:" in signal.upside_thesis
    assert "Downside risk:" in signal.downside_risk
    assert "Volatility context:" in signal.volatility_context
    assert "Liquidity context:" in signal.liquidity_context
    assert signal.headline_context
    assert signal.decision_trace[-2].stage == "explanation"
    assert "Data limitations:" in signal.decision_trace[-2].reason


def test_outbox_idempotency_prevents_duplicate_publication() -> None:
    repository = InMemorySignalLedgerRepository()

    repository.append_outbox(
        tenant_id=TENANT_ID,
        event_type="unit.test",
        aggregate_type="clean_signal",
        aggregate_id="signal_1",
        idempotency_key="unit:test:signal_1",
        payload={"signal_id": "signal_1"},
        created_at=NOW,
    )

    with pytest.raises(SignalLedgerError, match="duplicate"):
        repository.append_outbox(
            tenant_id=TENANT_ID,
            event_type="unit.test",
            aggregate_type="clean_signal",
            aggregate_id="signal_1",
            idempotency_key="unit:test:signal_1",
            payload={"signal_id": "signal_1"},
            created_at=NOW,
        )
