from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256

from zulu_contracts import (
    AssetType,
    CanonicalFeatureVectorV1,
    SignalDirection,
    StrategyCandidate,
    Timeframe,
)


@dataclass(frozen=True)
class StrategyContext:
    tenant_id: str
    ticker: str
    feature_vector: CanonicalFeatureVectorV1
    generated_at: datetime
    asset_type: AssetType = AssetType.STOCK


class StrategyModule(ABC):
    setup_type: str

    @abstractmethod
    def generate(self, context: StrategyContext) -> StrategyCandidate | None:
        """Return one deterministic candidate or no candidate when setup criteria are absent."""


class MomentumContinuationStrategy(StrategyModule):
    setup_type = "momentum_continuation"

    def generate(self, context: StrategyContext) -> StrategyCandidate | None:
        features = context.feature_vector.feature_values
        if (
            features["canonical_v1.trend.close_vs_prior_close"] < Decimal("0.012")
            or features["canonical_v1.relative_volume.latest_vs_prior"] < Decimal("1.10")
            or features["canonical_v1.weather.risk_on_score"] < Decimal("0.50")
        ):
            return None
        return _candidate(
            context,
            setup_type=self.setup_type,
            direction=SignalDirection.LONG,
            rationale=(
                "Momentum continuation candidate: price is advancing versus the prior close, "
                "relative volume is elevated, and broad market posture is not risk-off."
            ),
        )


class VwapReclaimRejectStrategy(StrategyModule):
    setup_type = "vwap_reclaim_reject"

    def generate(self, context: StrategyContext) -> StrategyCandidate | None:
        features = context.feature_vector.feature_values
        vwap_delta = features["canonical_v1.vwap.last_vs_vwap"]
        range_position = features["canonical_v1.trend.close_position_in_range"]
        if vwap_delta >= Decimal("0.003") and range_position >= Decimal("0.55"):
            return _candidate(
                context,
                setup_type=self.setup_type,
                direction=SignalDirection.LONG,
                rationale=(
                    "VWAP reclaim candidate: last price is above VWAP and price is holding in "
                    "the upper half of the recent range."
                ),
            )
        if vwap_delta <= Decimal("-0.003") and range_position <= Decimal("0.45"):
            return _candidate(
                context,
                setup_type=self.setup_type,
                direction=SignalDirection.SHORT,
                rationale=(
                    "VWAP reject candidate: last price is below VWAP and price is holding in "
                    "the lower half of the recent range."
                ),
            )
        return None


class VolatilityExpansionStrategy(StrategyModule):
    setup_type = "volatility_expansion"

    def generate(self, context: StrategyContext) -> StrategyCandidate | None:
        features = context.feature_vector.feature_values
        if features["canonical_v1.atr.latest_range_vs_atr_proxy"] < Decimal("1.15") or features[
            "canonical_v1.relative_volume.latest_vs_prior"
        ] < Decimal("1.05"):
            return None
        direction = (
            SignalDirection.LONG
            if features["canonical_v1.momentum.intrabar_return"] >= Decimal("0")
            else SignalDirection.SHORT
        )
        return _candidate(
            context,
            setup_type=self.setup_type,
            direction=direction,
            rationale=(
                "Volatility expansion candidate: current range is expanding relative to the "
                "ATR proxy with supportive relative volume."
            ),
        )


class GapContinuationFadeStrategy(StrategyModule):
    setup_type = "gap_continuation_fade"

    def generate(self, context: StrategyContext) -> StrategyCandidate | None:
        features = context.feature_vector.feature_values
        gap = features["canonical_v1.gap.open_vs_prior_close"]
        reclaim = features["canonical_v1.vwap.last_vs_vwap"]
        if abs(gap) < Decimal("0.012"):
            return None
        direction = (
            SignalDirection.LONG if gap > 0 and reclaim >= Decimal("0") else SignalDirection.SHORT
        )
        return _candidate(
            context,
            setup_type=self.setup_type,
            direction=direction,
            rationale=(
                "Gap continuation/fade candidate: the open materially diverged from the prior "
                "close and VWAP context defines whether continuation or fade is favored."
            ),
        )


class OptionsUnusualActivityStrategy(StrategyModule):
    setup_type = "options_unusual_activity"

    def generate(self, context: StrategyContext) -> StrategyCandidate | None:
        features = context.feature_vector.feature_values
        if (
            features["canonical_v1.options.contract_present"] != Decimal("1.000000")
            or features["canonical_v1.options.liquidity_score"] < Decimal("0.55")
            or features["canonical_v1.options.volume_score"] < Decimal("0.50")
            or features["canonical_v1.options.open_interest_score"] < Decimal("0.30")
        ):
            return None
        direction = (
            (
                SignalDirection.LONG
                if features["canonical_v1.options.delta"] >= Decimal("0")
                else SignalDirection.SHORT
            )
            if "canonical_v1.options.delta" in features
            else SignalDirection.LONG
        )
        return _candidate(
            context,
            setup_type=self.setup_type,
            direction=direction,
            asset_type=AssetType.OPTION,
            rationale=(
                "Options unusual activity candidate: option liquidity, volume, and open "
                "interest inputs are sufficient for an options-specific review."
            ),
        )


class PullbackSupportResistanceStrategy(StrategyModule):
    setup_type = "pullback_support_resistance"

    def generate(self, context: StrategyContext) -> StrategyCandidate | None:
        features = context.feature_vector.feature_values
        support_distance = features["canonical_v1.support.distance_to_recent_low"]
        resistance_distance = features["canonical_v1.resistance.distance_to_recent_high"]
        if support_distance <= Decimal("0.030") and features[
            "canonical_v1.vwap.last_vs_vwap"
        ] >= Decimal("0"):
            return _candidate(
                context,
                setup_type=self.setup_type,
                direction=SignalDirection.LONG,
                rationale=(
                    "Pullback-to-support candidate: price is close to recent support while "
                    "holding at or above VWAP."
                ),
            )
        if resistance_distance <= Decimal("0.030") and features[
            "canonical_v1.vwap.last_vs_vwap"
        ] <= Decimal("0"):
            return _candidate(
                context,
                setup_type=self.setup_type,
                direction=SignalDirection.SHORT,
                rationale=(
                    "Pullback-to-resistance candidate: price is close to recent resistance "
                    "while failing to reclaim VWAP."
                ),
            )
        return None


def default_strategy_modules() -> tuple[StrategyModule, ...]:
    return (
        MomentumContinuationStrategy(),
        VwapReclaimRejectStrategy(),
        VolatilityExpansionStrategy(),
        GapContinuationFadeStrategy(),
        OptionsUnusualActivityStrategy(),
        PullbackSupportResistanceStrategy(),
    )


def _candidate(
    context: StrategyContext,
    *,
    setup_type: str,
    direction: SignalDirection,
    rationale: str,
    asset_type: AssetType | None = None,
) -> StrategyCandidate:
    selected_asset_type = asset_type or context.asset_type
    return StrategyCandidate(
        strategy_candidate_id=_candidate_id(context, setup_type, direction, selected_asset_type),
        tenant_id=context.tenant_id,
        asset_type=selected_asset_type,
        ticker=context.ticker.upper(),
        direction=direction,
        timeframe=Timeframe.INTRADAY,
        feature_vector=context.feature_vector,
        rationale=rationale,
        created_at=context.generated_at,
    )


def _candidate_id(
    context: StrategyContext,
    setup_type: str,
    direction: SignalDirection,
    asset_type: AssetType,
) -> str:
    seed = (
        f"{context.tenant_id}:{context.ticker.upper()}:{setup_type}:"
        f"{direction.value}:{asset_type.value}:{context.feature_vector.content_hash}"
    )
    return f"candidate_{sha256(seed.encode()).hexdigest()[:20]}"
