from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from zulu_contracts import StrategyCandidate


@dataclass(frozen=True)
class ScoreComponent:
    name: str
    value: Decimal
    rationale: str


@dataclass(frozen=True)
class CandidateScore:
    confidence_score: Decimal
    risk_score: Decimal
    quality_score: Decimal
    model_manifest_id: str
    model_mode: str
    components: tuple[ScoreComponent, ...]
    limitations: tuple[str, ...]


class CandidateScorer(Protocol):
    def score(self, candidate: StrategyCandidate) -> CandidateScore: ...


class CalibrationHook(Protocol):
    def calibrate(self, score: CandidateScore) -> CandidateScore: ...


class NoopCalibrationHook:
    def calibrate(self, score: CandidateScore) -> CandidateScore:
        return score


class BaselineCandidateScorer:
    model_manifest_id = "baseline_signal_scorer_v1"
    model_mode = "baseline"

    def __init__(self, calibration_hook: CalibrationHook | None = None) -> None:
        self.calibration_hook = calibration_hook or NoopCalibrationHook()

    def score(self, candidate: StrategyCandidate) -> CandidateScore:
        features = candidate.feature_vector.feature_values
        confidence_components = (
            ScoreComponent(
                "trend_alignment",
                _positive_score(features["canonical_v1.trend.close_vs_prior_close"]),
                "trend alignment supports confidence when current price is improving",
            ),
            ScoreComponent(
                "vwap_alignment",
                _positive_score(features["canonical_v1.vwap.last_vs_vwap"]),
                "VWAP alignment supports confidence when price is holding the preferred side",
            ),
            ScoreComponent(
                "relative_volume",
                min(
                    Decimal("1"),
                    features["canonical_v1.relative_volume.latest_vs_prior"] / Decimal("2"),
                ),
                "relative volume supports confidence when participation is above baseline",
            ),
            ScoreComponent(
                "market_weather",
                features["canonical_v1.weather.risk_on_score"],
                "market weather affects confidence through broad risk posture",
            ),
            ScoreComponent(
                "headline_pressure",
                _sentiment_to_score(features["canonical_v1.headline.sentiment_pressure"]),
                "headline pressure adjusts confidence conservatively",
            ),
        )
        confidence = _average(component.value for component in confidence_components)
        risk_components = (
            ScoreComponent(
                "spread_risk",
                min(
                    Decimal("1"),
                    features["canonical_v1.spread.quote_spread_fraction"] * Decimal("30"),
                ),
                "wide spreads increase execution risk",
            ),
            ScoreComponent(
                "volatility_risk",
                min(
                    Decimal("1"),
                    features["canonical_v1.volatility.atr_proxy_fraction"] * Decimal("20"),
                ),
                "larger ATR proxy values increase setup risk",
            ),
            ScoreComponent(
                "weather_risk_off",
                features["canonical_v1.weather.regime_risk_off"],
                "risk-off weather increases setup risk",
            ),
            ScoreComponent(
                "options_liquidity_risk",
                Decimal("1") - features["canonical_v1.options.liquidity_score"],
                "weak options liquidity increases setup risk when an option contract is involved",
            ),
        )
        if candidate.asset_type.value == "stock":
            risk_values = [
                risk_components[0].value,
                risk_components[1].value,
                risk_components[2].value,
            ]
        else:
            risk_values = [component.value for component in risk_components]
        risk = _average(risk_values)
        missing_limitations = _missing_data_limitations(features)
        if missing_limitations:
            confidence -= Decimal("0.08") * Decimal(len(missing_limitations))
        confidence = _clamp01(confidence)
        risk = _clamp01(risk)
        quality = _clamp01(
            (confidence * Decimal("0.70")) + ((Decimal("1") - risk) * Decimal("0.30"))
        )
        return self.calibration_hook.calibrate(
            CandidateScore(
                confidence_score=confidence,
                risk_score=risk,
                quality_score=quality,
                model_manifest_id=self.model_manifest_id,
                model_mode=self.model_mode,
                components=confidence_components + risk_components,
                limitations=missing_limitations,
            )
        )


def _missing_data_limitations(features: dict[str, Decimal]) -> tuple[str, ...]:
    limitations: list[str] = []
    if features["canonical_v1.options.contract_present"] == Decimal("1.000000"):
        if features["canonical_v1.options.greeks_available"] == Decimal("0.000000"):
            limitations.append("options greeks unavailable")
        if features["canonical_v1.options.implied_volatility_available"] == Decimal("0.000000"):
            limitations.append("options implied volatility unavailable")
    return tuple(limitations)


def _average(values: Iterable[Decimal]) -> Decimal:
    materialized = tuple(values)
    if not materialized:
        return Decimal("0")
    return sum(materialized, Decimal("0")) / Decimal(len(materialized))


def _positive_score(value: Decimal) -> Decimal:
    return _clamp01((value + Decimal("0.03")) / Decimal("0.06"))


def _sentiment_to_score(value: Decimal) -> Decimal:
    return _clamp01((value + Decimal("1")) / Decimal("2"))


def _clamp01(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("1"), value)).quantize(Decimal("0.000001"))
