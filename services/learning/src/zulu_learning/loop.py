from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from zulu_learning.analysis import FailurePatternAnalyzer
from zulu_learning.models import LearningCycleReport
from zulu_learning.repository import InMemoryLearningRepository


class BoundedLearningLoop:
    def __init__(
        self,
        repository: InMemoryLearningRepository,
        *,
        analyzer: FailurePatternAnalyzer | None = None,
    ) -> None:
        self.repository = repository
        self.analyzer = analyzer or FailurePatternAnalyzer()

    def run_cycle(self, *, tenant_id: str, created_at: datetime) -> LearningCycleReport:
        outcomes = tuple(self.repository.trade_outcomes.values())
        near_misses = tuple(self.repository.near_misses.values())
        failure_modes = self.analyzer.recurring_failure_modes(
            outcomes=outcomes,
            near_misses=near_misses,
        )
        degrading = self.analyzer.degrading_strategy_regimes(outcomes=outcomes)
        proposed = tuple(f"evaluate mitigation for {mode}" for mode in failure_modes[:5])
        tasks = tuple(f"shadow-evaluate {proposal}" for proposal in proposed)
        report = LearningCycleReport(
            cycle_id=_id("learning_cycle", tenant_id, created_at.isoformat()),
            tenant_id=tenant_id,
            created_at=created_at,
            outcome_labels_created=len(outcomes),
            near_miss_labels_created=len(near_misses),
            recurring_failure_modes=failure_modes,
            degrading_strategy_regimes=degrading,
            proposed_improvements=proposed,
            evaluation_tasks=tasks,
            live_mutation_attempted=False,
        )
        self.repository.add_cycle_report(report)
        return report


def _id(prefix: str, *parts: str) -> str:
    digest = sha256(":".join(parts).encode()).hexdigest()
    return f"{prefix}_{digest[:24]}"
