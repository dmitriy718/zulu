from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from zulu_contracts import AssetType, CleanSignalV1, SignalDirection


class SignalQualityError(ValueError):
    pass


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    reasons: tuple[str, ...]


class SignalQualityGate:
    min_quality_score: Decimal = Decimal("0.45")
    min_confidence_score: Decimal = Decimal("0.35")
    max_risk_score: Decimal = Decimal("0.80")
    min_reward_to_risk: Decimal = Decimal("1.20")

    def evaluate(self, signal: CleanSignalV1, *, now: datetime) -> QualityGateResult:
        reasons: list[str] = []
        if signal.asset_type not in {AssetType.STOCK, AssetType.OPTION}:
            reasons.append("unsupported asset type")
        if signal.asset_type == AssetType.OPTION and signal.option_contract is None:
            reasons.append("options contract metadata missing")
        if signal.stop_loss <= Decimal("0"):
            reasons.append("missing stop loss")
        if signal.entry_trigger.strip() == "":
            reasons.append("missing entry trigger")
        if signal.entry_zone.upper < signal.entry_zone.lower:
            reasons.append("invalid entry zone")
        if signal.market_data_snapshot.expires_at <= now:
            reasons.append("stale market data")
        if signal.market_weather.expires_at <= now:
            reasons.append("missing market weather snapshot")
        if not signal.feature_vector.feature_values:
            reasons.append("empty feature vector")
        if not signal.decision_trace:
            reasons.append("missing decision trace")
        if signal.expires_at <= now:
            reasons.append("expired signal timestamp")
        if len(signal.take_profit_levels) == 0:
            reasons.append("invalid take-profit ladder")
        if sum(level.scale_out_fraction for level in signal.take_profit_levels) > Decimal("1"):
            reasons.append("invalid take-profit ladder")
        if self._reward_to_risk(signal) < self.min_reward_to_risk:
            reasons.append("nonsensical risk/reward")
        if signal.quality_score < self.min_quality_score:
            reasons.append("quality score below acceptance floor")
        if signal.confidence_score < self.min_confidence_score:
            reasons.append("confidence score below acceptance floor")
        if signal.risk_score > self.max_risk_score:
            reasons.append("risk score above acceptance ceiling")
        return QualityGateResult(passed=not reasons, reasons=tuple(reasons))

    def require_pass(self, signal: CleanSignalV1, *, now: datetime) -> None:
        result = self.evaluate(signal, now=now)
        if not result.passed:
            raise SignalQualityError("; ".join(result.reasons))

    def _reward_to_risk(self, signal: CleanSignalV1) -> Decimal:
        entry_mid = (signal.entry_zone.lower + signal.entry_zone.upper) / Decimal("2")
        if signal.direction == SignalDirection.LONG:
            risk = entry_mid - signal.stop_loss
            reward = max(level.price for level in signal.take_profit_levels) - entry_mid
        else:
            risk = signal.stop_loss - entry_mid
            reward = entry_mid - min(level.price for level in signal.take_profit_levels)
        if risk <= Decimal("0"):
            return Decimal("0")
        return reward / risk
