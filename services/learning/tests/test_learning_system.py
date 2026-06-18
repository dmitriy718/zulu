from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from zulu_contracts import AssetType, CleanSignalV1, ModelManifest
from zulu_learning import (
    BoundedLearningLoop,
    DatasetSplit,
    HistoricalSignalRecord,
    InMemoryLearningRepository,
    LearningModel,
    LookaheadBiasError,
    ModelRegistry,
    ModelStatus,
    NearMissDetails,
    NearMissLabeler,
    OutcomeLabelDetails,
    OutcomeLabeler,
    PromotionGateWorkflow,
    PromotionStage,
    ReplayEngine,
)
from zulu_policy import ExecutionEnvironment, PolicyContext, SubscriptionMode
from zulu_risk import RiskContext, RiskLimits
from zulu_signal_intelligence.fixture_provider import FixtureMarketDataProvider
from zulu_signal_intelligence.ledger import InMemorySignalLedgerRepository
from zulu_signal_intelligence.pipeline import SignalIntelligencePipeline

NOW = datetime(2026, 6, 18, 14, 30, tzinfo=UTC)


def _clean_signal() -> CleanSignalV1:
    result = SignalIntelligencePipeline(
        provider=FixtureMarketDataProvider(now=NOW),
        repository=InMemorySignalLedgerRepository(),
    ).run(
        tenant_id="tenant_1",
        ticker="MSFT",
        user_id="user_1",
        actor_id="learning_test",
        correlation_id="learning_test",
        now=NOW,
    )
    assert result.accepted_signal is not None
    return result.accepted_signal


def _policy_context(_record: HistoricalSignalRecord) -> PolicyContext:
    return PolicyContext(
        tenant_id="tenant_1",
        user_id="user_1",
        user_approved_signal=True,
        instrument_allowed=True,
        policy_version="policy-learning-v1",
        subscription_mode=SubscriptionMode.PAPER_AUTOMATION,
        user_automation_permission=True,
        environment=ExecutionEnvironment.PAPER,
        supported_asset_types=frozenset({AssetType.STOCK}),
        now=NOW,
    )


def _risk_context(_record: HistoricalSignalRecord) -> RiskContext:
    return RiskContext(
        tenant_id="tenant_1",
        user_id="user_1",
        now=NOW,
        order_notional=Decimal("1000"),
        estimated_max_loss=Decimal("100"),
        requested_quantity=Decimal("1"),
    )


def _model_manifest() -> ModelManifest:
    return ModelManifest(
        model_manifest_id="model_baseline_v2",
        tenant_id="tenant_1",
        model_name="baseline-scorer",
        model_version="2",
        feature_schema_version="canonical_features_v1",
        artifact_uri="registry://baseline-scorer/2",
        training_data_hash="a" * 64,
        created_at=NOW,
    )


def _learning_model(status: ModelStatus = ModelStatus.PAPER) -> LearningModel:
    return LearningModel(
        manifest=_model_manifest(),
        status=status,
        training_window_start=NOW - timedelta(days=120),
        training_window_end=NOW - timedelta(days=30),
        excluded_windows=((NOW - timedelta(days=60), NOW - timedelta(days=55)),),
        calibration_report="baseline calibration requires more labeled live-independent data",
        known_weaknesses=("risk-off chop",),
        allowed_asset_types=frozenset({AssetType.STOCK}),
        allowed_strategy_types=frozenset({"vwap_reclaim_reject"}),
    )


def test_trade_outcome_label_includes_required_details() -> None:
    repository = InMemoryLearningRepository()
    signal = _clean_signal()

    outcome = OutcomeLabeler(repository).label_trade(
        signal=signal,
        details=OutcomeLabelDetails(
            final_pnl=Decimal("125.50"),
            max_favorable_excursion=Decimal("250.00"),
            max_adverse_excursion=Decimal("50.00"),
            take_profit_levels_reached=("tp1",),
            stop_loss_reached=False,
            entry_trigger_fired=True,
            signal_expired=False,
            market_regime_at_entry="risk_on",
            market_regime_at_exit="balanced",
            data_quality_limitations=("options greeks unavailable",),
            execution_quality_notes="paper fill matched entry constraints",
        ),
        labeled_at=NOW + timedelta(hours=1),
    )

    assert outcome.label.label == "win"
    assert outcome.details.final_pnl == Decimal("125.50")
    assert outcome.details.take_profit_levels_reached == ("tp1",)
    assert repository.trade_outcomes[outcome.label.trade_outcome_id] == outcome


def test_near_miss_label_captures_skipped_signal_context() -> None:
    repository = InMemoryLearningRepository()
    signal = _clean_signal()

    near_miss = NearMissLabeler(repository).label_near_miss(
        signal=signal,
        details=NearMissDetails(
            entry_trigger_fired=True,
            signal_expired=False,
            take_profit_levels_reached=("tp1", "tp2"),
            stop_loss_would_have_been_reached=False,
            market_regime_at_signal="risk_on",
            market_regime_after_signal="risk_on",
            data_quality_limitations=(),
            execution_quality_notes="skipped by user before paper routing",
            rejection_or_skip_reason="user skipped automation",
        ),
        labeled_at=NOW + timedelta(hours=1),
    )

    assert near_miss.label.would_have_triggered is True
    assert near_miss.details.rejection_or_skip_reason == "user skipped automation"
    assert repository.near_misses[near_miss.label.near_miss_id] == near_miss


def test_replay_is_deterministic_and_separates_splits() -> None:
    repository = InMemoryLearningRepository()
    signal = _clean_signal()
    record = HistoricalSignalRecord(
        signal=signal,
        old_policy_decision="old policy allowed",
        old_risk_decision="old risk allowed",
        data_available_at=signal.created_at + timedelta(seconds=1),
        split=DatasetSplit.SHADOW,
    )
    engine = ReplayEngine(repository)

    first = engine.replay(
        tenant_id="tenant_1",
        records=(record,),
        replayed_at=NOW + timedelta(days=1),
        policy_context_factory=_policy_context,
        risk_context_factory=_risk_context,
        risk_limits=RiskLimits(
            max_order_notional=Decimal("10000"),
            max_symbol_exposure=Decimal("25000"),
        ),
    )
    second = engine.replay(
        tenant_id="tenant_1",
        records=(record,),
        replayed_at=NOW + timedelta(days=1),
        policy_context_factory=_policy_context,
        risk_context_factory=_risk_context,
        risk_limits=RiskLimits(
            max_order_notional=Decimal("10000"),
            max_symbol_exposure=Decimal("25000"),
        ),
    )

    assert first.comparisons == second.comparisons
    assert first.split_counts[DatasetSplit.SHADOW] == 1
    assert first.no_lookahead_verified is True


def test_replay_rejects_lookahead_data() -> None:
    signal = _clean_signal()
    record = HistoricalSignalRecord(
        signal=signal,
        old_policy_decision="old policy allowed",
        old_risk_decision="old risk allowed",
        data_available_at=NOW + timedelta(days=2),
        split=DatasetSplit.TEST,
    )

    with pytest.raises(LookaheadBiasError):
        ReplayEngine(InMemoryLearningRepository()).replay(
            tenant_id="tenant_1",
            records=(record,),
            replayed_at=NOW + timedelta(days=1),
            policy_context_factory=_policy_context,
            risk_context_factory=_risk_context,
            risk_limits=RiskLimits(
                max_order_notional=Decimal("10000"),
                max_symbol_exposure=Decimal("25000"),
            ),
        )


def test_model_registry_stores_manifest_and_evaluation_report() -> None:
    repository = InMemoryLearningRepository()
    registry = ModelRegistry(repository)
    model = registry.register(_learning_model())
    report = registry.create_evaluation_report(
        manifest=model.manifest,
        evaluation_window_start=NOW - timedelta(days=30),
        evaluation_window_end=NOW,
        labeled_outcome_count=250,
        metrics={"precision": Decimal("0.620000"), "calibration_error": Decimal("0.080000")},
        promotion_approved=True,
        created_at=NOW,
    )

    assert registry.get(model.manifest.model_manifest_id) == model
    assert repository.evaluation_reports[report.model_evaluation_report_id] == report


def test_promotion_gate_requires_all_stages_and_records_promotion() -> None:
    repository = InMemoryLearningRepository()
    registry = ModelRegistry(repository)
    model = registry.register(_learning_model(status=ModelStatus.PAPER))
    report = registry.create_evaluation_report(
        manifest=model.manifest,
        evaluation_window_start=NOW - timedelta(days=30),
        evaluation_window_end=NOW,
        labeled_outcome_count=250,
        metrics={"precision": Decimal("0.620000")},
        promotion_approved=True,
        created_at=NOW,
    )

    rejected = PromotionGateWorkflow(repository).evaluate_promotion(
        model=model,
        to_status=ModelStatus.APPROVED,
        completed_stages=frozenset({PromotionStage.CANDIDATE_EVALUATION}),
        evaluation_report_id=report.model_evaluation_report_id,
        risk_review_record_id="risk_review_1",
        rollback_plan="revert to baseline scorer",
        promoted_by="reviewer_1",
        promoted_at=NOW,
    )
    approved = PromotionGateWorkflow(repository).evaluate_promotion(
        model=model,
        to_status=ModelStatus.APPROVED,
        completed_stages=PromotionGateWorkflow.required_stages,
        evaluation_report_id=report.model_evaluation_report_id,
        risk_review_record_id="risk_review_1",
        rollback_plan="revert to baseline scorer",
        promoted_by="reviewer_1",
        promoted_at=NOW,
    )

    assert rejected.approved is False
    assert "missing stages" in rejected.reason
    assert approved.approved is True
    assert repository.promotion_records[-1].audit_event_id.startswith("audit_")


def test_bounded_learning_loop_recommends_without_live_mutation() -> None:
    repository = InMemoryLearningRepository()
    signal = _clean_signal()
    OutcomeLabeler(repository).label_trade(
        signal=signal,
        details=OutcomeLabelDetails(
            final_pnl=Decimal("-75.00"),
            max_favorable_excursion=Decimal("20.00"),
            max_adverse_excursion=Decimal("100.00"),
            stop_loss_reached=True,
            entry_trigger_fired=True,
            signal_expired=False,
            market_regime_at_entry="risk_off",
            market_regime_at_exit="risk_off",
            data_quality_limitations=("wide spread",),
            execution_quality_notes="slippage observed in paper fill",
        ),
        labeled_at=NOW + timedelta(hours=1),
    )

    report = BoundedLearningLoop(repository).run_cycle(
        tenant_id="tenant_1",
        created_at=NOW + timedelta(hours=2),
    )

    assert "stop_loss_reached" in report.recurring_failure_modes
    assert report.proposed_improvements
    assert report.evaluation_tasks
    assert report.live_mutation_attempted is False
