from datetime import datetime
from hashlib import sha256

from pydantic import BaseModel, Field

from zulu_learning.models import LearningModel, ModelStatus, PromotionRecord, PromotionStage
from zulu_learning.repository import InMemoryLearningRepository


class ModelEvaluationSummary(BaseModel):
    model_id: str = Field(min_length=1)
    labeled_outcome_count: int = Field(ge=0)
    evaluation_window_days: int = Field(gt=0)
    approved_for_promotion: bool = False


class PromotionDecision(BaseModel):
    approved: bool
    reason: str


class PromotionGate:
    def evaluate(self, summary: ModelEvaluationSummary) -> PromotionDecision:
        if summary.labeled_outcome_count < 100:
            return PromotionDecision(
                approved=False,
                reason="insufficient labeled outcomes for promotion review",
            )
        if not summary.approved_for_promotion:
            return PromotionDecision(
                approved=False,
                reason="model has not passed independent promotion review",
            )
        return PromotionDecision(approved=True, reason="promotion gates passed")


class PromotionGateWorkflow:
    required_stages = frozenset(
        {
            PromotionStage.CANDIDATE_EVALUATION,
            PromotionStage.SHADOW_MODE,
            PromotionStage.PAPER_MODE,
            PromotionStage.EVALUATION_REPORT,
            PromotionStage.RISK_REVIEW,
            PromotionStage.PROMOTION_EVENT,
            PromotionStage.ROLLBACK_PLAN,
        }
    )

    def __init__(self, repository: InMemoryLearningRepository) -> None:
        self.repository = repository

    def evaluate_promotion(
        self,
        *,
        model: LearningModel,
        to_status: ModelStatus,
        completed_stages: frozenset[PromotionStage],
        evaluation_report_id: str,
        risk_review_record_id: str,
        rollback_plan: str,
        promoted_by: str,
        promoted_at: datetime,
    ) -> PromotionDecision:
        missing = self.required_stages - completed_stages
        if missing:
            missing_stage_names = ", ".join(sorted(stage.value for stage in missing))
            return PromotionDecision(
                approved=False,
                reason=f"promotion missing stages: {missing_stage_names}",
            )
        if evaluation_report_id not in self.repository.evaluation_reports:
            return PromotionDecision(approved=False, reason="evaluation report is required")
        if to_status == ModelStatus.APPROVED and model.status != ModelStatus.PAPER:
            return PromotionDecision(
                approved=False,
                reason="approval requires candidate to complete paper mode first",
            )
        record = PromotionRecord(
            model_manifest_id=model.manifest.model_manifest_id,
            from_status=model.status,
            to_status=to_status,
            completed_stages=completed_stages,
            evaluation_report_id=evaluation_report_id,
            risk_review_record_id=risk_review_record_id,
            rollback_plan=rollback_plan,
            promoted_by=promoted_by,
            promoted_at=promoted_at,
            audit_event_id=_id("audit", model.manifest.model_manifest_id, promoted_at.isoformat()),
        )
        self.repository.add_promotion_record(record)
        return PromotionDecision(approved=True, reason="promotion gates passed")


def _id(prefix: str, *parts: str) -> str:
    digest = sha256(":".join(parts).encode()).hexdigest()
    return f"{prefix}_{digest[:24]}"
