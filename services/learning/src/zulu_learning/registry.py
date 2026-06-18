from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from hashlib import sha256

from zulu_contracts import ModelEvaluationReport, ModelManifest

from zulu_learning.models import LearningModel
from zulu_learning.repository import InMemoryLearningRepository


class ModelRegistry:
    def __init__(self, repository: InMemoryLearningRepository) -> None:
        self.repository = repository

    def register(self, model: LearningModel) -> LearningModel:
        self.repository.add_model(model)
        return model

    def create_evaluation_report(
        self,
        *,
        manifest: ModelManifest,
        evaluation_window_start: datetime,
        evaluation_window_end: datetime,
        labeled_outcome_count: int,
        metrics: dict[str, Decimal],
        promotion_approved: bool,
        created_at: datetime,
    ) -> ModelEvaluationReport:
        report = ModelEvaluationReport(
            model_evaluation_report_id=_id(
                "model_eval",
                manifest.model_manifest_id,
                evaluation_window_start.isoformat(),
                evaluation_window_end.isoformat(),
            ),
            tenant_id=manifest.tenant_id,
            model_manifest_id=manifest.model_manifest_id,
            evaluation_window_start=evaluation_window_start,
            evaluation_window_end=evaluation_window_end,
            labeled_outcome_count=labeled_outcome_count,
            metrics=metrics,
            promotion_approved=promotion_approved,
            created_at=created_at,
        )
        self.repository.add_evaluation_report(report)
        return report

    def get(self, model_manifest_id: str) -> LearningModel:
        return self.repository.models[model_manifest_id]


def _id(prefix: str, *parts: str) -> str:
    digest = sha256(":".join(parts).encode()).hexdigest()
    return f"{prefix}_{digest[:24]}"
