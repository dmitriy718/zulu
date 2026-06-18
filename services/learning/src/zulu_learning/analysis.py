from __future__ import annotations

from collections import Counter

from zulu_learning.models import DurableNearMiss, DurableTradeOutcome


class FailurePatternAnalyzer:
    def recurring_failure_modes(
        self,
        *,
        outcomes: tuple[DurableTradeOutcome, ...],
        near_misses: tuple[DurableNearMiss, ...],
    ) -> tuple[str, ...]:
        counter: Counter[str] = Counter()
        for outcome in outcomes:
            if outcome.label.label in {"loss", "stopped_out"}:
                counter.update(outcome.details.data_quality_limitations)
                if outcome.details.stop_loss_reached:
                    counter["stop_loss_reached"] += 1
                if "slippage" in outcome.details.execution_quality_notes.lower():
                    counter["execution_slippage"] += 1
        for near_miss in near_misses:
            counter[near_miss.details.rejection_or_skip_reason] += 1
            counter.update(near_miss.details.data_quality_limitations)
        return tuple(reason for reason, count in counter.most_common() if count >= 1)

    def degrading_strategy_regimes(
        self,
        *,
        outcomes: tuple[DurableTradeOutcome, ...],
    ) -> tuple[str, ...]:
        losses_by_regime: Counter[str] = Counter()
        for outcome in outcomes:
            if outcome.label.label in {"loss", "stopped_out"}:
                losses_by_regime[outcome.details.market_regime_at_entry] += 1
        return tuple(
            f"{regime}:loss_count={count}" for regime, count in losses_by_regime.most_common()
        )
