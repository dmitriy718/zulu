from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import datetime
from hashlib import sha256

from zulu_policy import PolicyContext, PolicyGate
from zulu_risk import RiskContext, RiskGate, RiskLimits

from zulu_learning.models import (
    DatasetSplit,
    HistoricalSignalRecord,
    ReplayDecisionComparison,
    ReplayReport,
)
from zulu_learning.repository import InMemoryLearningRepository


class LookaheadBiasError(ValueError):
    pass


PolicyContextFactory = Callable[[HistoricalSignalRecord], PolicyContext]
RiskContextFactory = Callable[[HistoricalSignalRecord], RiskContext]


class ReplayEngine:
    def __init__(
        self,
        repository: InMemoryLearningRepository,
        *,
        policy_gate: PolicyGate | None = None,
        risk_gate: RiskGate | None = None,
    ) -> None:
        self.repository = repository
        self.policy_gate = policy_gate or PolicyGate()
        self.risk_gate = risk_gate or RiskGate()

    def replay(
        self,
        *,
        tenant_id: str,
        records: tuple[HistoricalSignalRecord, ...],
        replayed_at: datetime,
        policy_context_factory: PolicyContextFactory,
        risk_context_factory: RiskContextFactory,
        risk_limits: RiskLimits,
    ) -> ReplayReport:
        comparisons: list[ReplayDecisionComparison] = []
        split_counts: Counter[DatasetSplit] = Counter()
        for record in records:
            if record.data_available_at > replayed_at:
                raise LookaheadBiasError("historical record was not available at replay time")
            if record.data_available_at < record.signal.created_at:
                raise LookaheadBiasError("data availability predates signal creation")
            policy_decision = self.policy_gate.evaluate(
                policy_context_factory(record), record.signal
            )
            risk_decision = self.risk_gate.evaluate_signal(
                record.signal, risk_context_factory(record), risk_limits
            )
            split_counts[record.split] += 1
            comparisons.append(
                ReplayDecisionComparison(
                    signal_id=record.signal.signal_id,
                    split=record.split,
                    old_policy_decision=record.old_policy_decision,
                    new_policy_decision=policy_decision.reason,
                    old_risk_decision=record.old_risk_decision,
                    new_risk_decision=risk_decision.reason,
                    changed=(
                        record.old_policy_decision != policy_decision.reason
                        or record.old_risk_decision != risk_decision.reason
                    ),
                    data_available_at=record.data_available_at,
                )
            )
        report = ReplayReport(
            replay_report_id=_id("replay", tenant_id, replayed_at.isoformat(), str(len(records))),
            tenant_id=tenant_id,
            replayed_at=replayed_at,
            comparisons=tuple(comparisons),
            split_counts={split: split_counts[split] for split in DatasetSplit},
            no_lookahead_verified=True,
        )
        self.repository.add_replay_report(report)
        return report


def _id(prefix: str, *parts: str) -> str:
    digest = sha256(":".join(parts).encode()).hexdigest()
    return f"{prefix}_{digest[:24]}"
