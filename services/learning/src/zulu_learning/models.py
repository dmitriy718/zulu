from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from zulu_contracts import (
    AssetType,
    CleanSignalV1,
    ModelManifest,
    NearMissLabel,
    TradeOutcomeLabel,
)


class DatasetSplit(StrEnum):
    TRAINING = "training"
    VALIDATION = "validation"
    TEST = "test"
    SHADOW = "shadow"


class ModelStatus(StrEnum):
    CANDIDATE = "candidate"
    SHADOW = "shadow"
    PAPER = "paper"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    BLOCKED = "blocked"


class PromotionStage(StrEnum):
    CANDIDATE_EVALUATION = "candidate_evaluation"
    SHADOW_MODE = "shadow_mode"
    PAPER_MODE = "paper_mode"
    EVALUATION_REPORT = "evaluation_report"
    RISK_REVIEW = "risk_review"
    PROMOTION_EVENT = "promotion_event"
    ROLLBACK_PLAN = "rollback_plan"


class LearningModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    manifest: ModelManifest
    status: ModelStatus
    training_window_start: datetime
    training_window_end: datetime
    excluded_windows: tuple[tuple[datetime, datetime], ...] = ()
    calibration_report: str = Field(min_length=1, max_length=2000)
    known_weaknesses: tuple[str, ...] = Field(default_factory=tuple)
    allowed_asset_types: frozenset[AssetType] = Field(default_factory=frozenset)
    allowed_strategy_types: frozenset[str] = Field(default_factory=frozenset)

    @field_validator("training_window_start", "training_window_end")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> LearningModel:
        if self.training_window_end <= self.training_window_start:
            raise ValueError("training window end must be after start")
        for start, end in self.excluded_windows:
            if start.tzinfo is None or end.tzinfo is None:
                raise ValueError("excluded windows must be timezone-aware")
            if end <= start:
                raise ValueError("excluded window end must be after start")
        return self


class OutcomeLabelDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    final_pnl: Decimal
    max_favorable_excursion: Decimal = Field(ge=Decimal("0"))
    max_adverse_excursion: Decimal = Field(ge=Decimal("0"))
    take_profit_levels_reached: tuple[str, ...] = ()
    stop_loss_reached: bool
    entry_trigger_fired: bool
    signal_expired: bool
    market_regime_at_entry: str = Field(min_length=1, max_length=80)
    market_regime_at_exit: str = Field(min_length=1, max_length=80)
    data_quality_limitations: tuple[str, ...] = ()
    execution_quality_notes: str = Field(min_length=1, max_length=1000)
    rejection_or_skip_reason: str | None = Field(default=None, max_length=1000)


class DurableTradeOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    label: TradeOutcomeLabel
    details: OutcomeLabelDetails


class NearMissDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    entry_trigger_fired: bool
    signal_expired: bool
    take_profit_levels_reached: tuple[str, ...] = ()
    stop_loss_would_have_been_reached: bool
    market_regime_at_signal: str = Field(min_length=1, max_length=80)
    market_regime_after_signal: str = Field(min_length=1, max_length=80)
    data_quality_limitations: tuple[str, ...] = ()
    execution_quality_notes: str = Field(min_length=1, max_length=1000)
    rejection_or_skip_reason: str = Field(min_length=1, max_length=1000)


class DurableNearMiss(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    label: NearMissLabel
    details: NearMissDetails


class HistoricalSignalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    signal: CleanSignalV1
    old_policy_decision: str = Field(min_length=1, max_length=120)
    old_risk_decision: str = Field(min_length=1, max_length=120)
    data_available_at: datetime
    split: DatasetSplit

    @field_validator("data_available_at")
    @classmethod
    def validate_data_available_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("data availability timestamp must be timezone-aware")
        return value


class ReplayDecisionComparison(BaseModel):
    signal_id: str
    split: DatasetSplit
    old_policy_decision: str
    new_policy_decision: str
    old_risk_decision: str
    new_risk_decision: str
    changed: bool
    data_available_at: datetime


class ReplayReport(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    replay_report_id: str
    tenant_id: str
    replayed_at: datetime
    comparisons: tuple[ReplayDecisionComparison, ...]
    split_counts: dict[DatasetSplit, int]
    no_lookahead_verified: bool


class PromotionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    model_manifest_id: str
    from_status: ModelStatus
    to_status: ModelStatus
    completed_stages: frozenset[PromotionStage]
    evaluation_report_id: str
    risk_review_record_id: str
    rollback_plan: str = Field(min_length=1, max_length=2000)
    promoted_by: str = Field(min_length=1, max_length=80)
    promoted_at: datetime
    audit_event_id: str = Field(min_length=1, max_length=80)


class LearningCycleReport(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    cycle_id: str
    tenant_id: str
    created_at: datetime
    outcome_labels_created: int
    near_miss_labels_created: int
    recurring_failure_modes: tuple[str, ...]
    degrading_strategy_regimes: tuple[str, ...]
    proposed_improvements: tuple[str, ...]
    evaluation_tasks: tuple[str, ...]
    live_mutation_attempted: bool = False
