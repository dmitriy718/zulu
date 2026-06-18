from zulu_learning import ModelEvaluationSummary, PromotionGate, service_health


def test_learning_health_is_testable() -> None:
    assert service_health().service == "learning"


def test_promotion_gate_rejects_insufficient_outcomes() -> None:
    decision = PromotionGate().evaluate(
        ModelEvaluationSummary(
            model_id="candidate-model",
            labeled_outcome_count=10,
            evaluation_window_days=30,
        )
    )

    assert decision.approved is False
    assert "insufficient" in decision.reason


def test_promotion_gate_requires_independent_review() -> None:
    decision = PromotionGate().evaluate(
        ModelEvaluationSummary(
            model_id="candidate-model",
            labeled_outcome_count=500,
            evaluation_window_days=90,
        )
    )

    assert decision.approved is False
    assert "review" in decision.reason
