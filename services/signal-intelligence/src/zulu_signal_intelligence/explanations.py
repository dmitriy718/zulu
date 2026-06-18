from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from zulu_contracts import HeadlineContextItem, HeadlineEvent, StrategyCandidate, TakeProfitLevel

from zulu_signal_intelligence.context_service import MarketContextBundle
from zulu_signal_intelligence.scoring import CandidateScore


@dataclass(frozen=True)
class SignalExplanation:
    technical_context: str
    volatility_context: str
    liquidity_context: str
    upside_thesis: str
    downside_risk: str
    invalidation_conditions: tuple[str, ...]
    headline_context: tuple[HeadlineContextItem, ...]
    confidence_explanation: str
    risk_explanation: str
    data_limitations: str


class SignalExplanationGenerator:
    def generate(
        self,
        *,
        candidate: StrategyCandidate,
        score: CandidateScore,
        context: MarketContextBundle,
        entry_trigger: str,
        stop_loss: Decimal,
        take_profit_levels: list[TakeProfitLevel],
    ) -> SignalExplanation:
        feature_values = candidate.feature_vector.feature_values
        setup_type = _setup_type(candidate.rationale)
        headlines = tuple(_headline_context_item(headline) for headline in context.headlines)
        tp_text = ", ".join(f"{level.label} at {level.price}" for level in take_profit_levels)
        limitations = (
            "; ".join(score.limitations) if score.limitations else "no key data limitations"
        )
        return SignalExplanation(
            technical_context=(
                f"What got attention: {setup_type}. Entry condition: {entry_trigger}. "
                f"VWAP relationship is {feature_values['canonical_v1.vwap.last_vs_vwap']} and "
                "relative volume is "
                f"{feature_values['canonical_v1.relative_volume.latest_vs_prior']}."
            ),
            volatility_context=(
                "Volatility context: ATR proxy fraction is "
                f"{feature_values['canonical_v1.volatility.atr_proxy_fraction']} and market "
                f"volatility regime is {context.market_weather.volatility_regime}."
            ),
            liquidity_context=(
                "Liquidity context: quote spread fraction is "
                f"{feature_values['canonical_v1.spread.quote_spread_fraction']} and volume "
                f"feature is {feature_values['canonical_v1.liquidity.volume_millions']} million."
            ),
            upside_thesis=(
                f"Setup type: {setup_type}. Upside thesis depends on trigger confirmation, "
                f"market weather staying {context.market_weather.regime}, and take-profit "
                f"ladder {tp_text}."
            ),
            downside_risk=(
                f"Downside risk: stop loss at {stop_loss}, setup failure if entry confirmation "
                "does not hold, or if broad market/headline context deteriorates."
            ),
            invalidation_conditions=(
                "price breaches the stop loss",
                "entry trigger fails before signal expiry",
                "market weather expires or turns materially worse",
                "provider data freshness or liquidity constraints fail",
            ),
            headline_context=headlines,
            confidence_explanation=(
                f"Confidence {score.confidence_score} uses {score.model_mode} scoring from "
                f"{', '.join(component.name for component in score.components[:5])}."
            ),
            risk_explanation=(
                f"Risk {score.risk_score} is separate from confidence and reflects spread, "
                "volatility, market weather, and options liquidity where applicable."
            ),
            data_limitations=f"Data limitations: {limitations}.",
        )


def _headline_context_item(headline: HeadlineEvent) -> HeadlineContextItem:
    return HeadlineContextItem(
        headline_event_id=headline.headline_event_id,
        relevance=f"{headline.title[:180]} from {headline.source}",
    )


def _setup_type(rationale: str) -> str:
    return rationale.split(" candidate:", maxsplit=1)[0].strip()
