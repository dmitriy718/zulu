from __future__ import annotations

from dataclasses import dataclass, field

from zulu_contracts import ModelEvaluationReport

from zulu_learning.models import (
    DurableNearMiss,
    DurableTradeOutcome,
    LearningCycleReport,
    LearningModel,
    PromotionRecord,
    ReplayReport,
)


@dataclass
class InMemoryLearningRepository:
    trade_outcomes: dict[str, DurableTradeOutcome] = field(default_factory=dict)
    near_misses: dict[str, DurableNearMiss] = field(default_factory=dict)
    models: dict[str, LearningModel] = field(default_factory=dict)
    evaluation_reports: dict[str, ModelEvaluationReport] = field(default_factory=dict)
    replay_reports: dict[str, ReplayReport] = field(default_factory=dict)
    promotion_records: list[PromotionRecord] = field(default_factory=list)
    cycle_reports: list[LearningCycleReport] = field(default_factory=list)

    def add_trade_outcome(self, outcome: DurableTradeOutcome) -> None:
        self.trade_outcomes[outcome.label.trade_outcome_id] = outcome

    def add_near_miss(self, near_miss: DurableNearMiss) -> None:
        self.near_misses[near_miss.label.near_miss_id] = near_miss

    def add_model(self, model: LearningModel) -> None:
        self.models[model.manifest.model_manifest_id] = model

    def add_evaluation_report(self, report: ModelEvaluationReport) -> None:
        self.evaluation_reports[report.model_evaluation_report_id] = report

    def add_replay_report(self, report: ReplayReport) -> None:
        self.replay_reports[report.replay_report_id] = report

    def add_promotion_record(self, record: PromotionRecord) -> None:
        self.promotion_records.append(record)

    def add_cycle_report(self, report: LearningCycleReport) -> None:
        self.cycle_reports.append(report)
