from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from zulu_contracts import HeadlineEvent, MarketWeatherSnapshot

from zulu_signal_intelligence.normalizers import normalize_market_weather
from zulu_signal_intelligence.provider_models import RawBroadMarketContext, RawMarketCalendar


@dataclass(frozen=True)
class WeatherComponent:
    name: str
    value: Decimal | str
    contribution: Decimal
    explanation: str


@dataclass(frozen=True)
class WeatherClassification:
    snapshot: MarketWeatherSnapshot
    components: tuple[WeatherComponent, ...]


class MarketWeatherService:
    def classify(
        self,
        *,
        tenant_id: str,
        broad_context: RawBroadMarketContext,
        calendar: RawMarketCalendar,
        headlines: list[HeadlineEvent],
        now: datetime,
    ) -> WeatherClassification:
        snapshot = normalize_market_weather(
            broad_context,
            calendar,
            headlines,
            tenant_id=tenant_id,
            now=now,
        )
        headline_pressure = Decimal("0")
        if headlines:
            headline_pressure = sum(
                (headline.sentiment_score for headline in headlines), Decimal("0")
            ) / Decimal(len(headlines))
        return WeatherClassification(
            snapshot=snapshot,
            components=(
                WeatherComponent(
                    name="index_trend",
                    value=broad_context.index_trend_score,
                    contribution=((broad_context.index_trend_score + Decimal("1")) / Decimal("2"))
                    * Decimal("0.25"),
                    explanation="normalized index trend contribution",
                ),
                WeatherComponent(
                    name="volatility_regime",
                    value=broad_context.volatility_index_level,
                    contribution=Decimal("0"),
                    explanation="volatility regime classifies elevated or normal conditions",
                ),
                WeatherComponent(
                    name="breadth_participation",
                    value=broad_context.breadth_score,
                    contribution=broad_context.breadth_score * Decimal("0.20"),
                    explanation="market breadth contribution",
                ),
                WeatherComponent(
                    name="sector_alignment",
                    value=broad_context.sector_alignment_score,
                    contribution=Decimal("0"),
                    explanation="sector alignment is exposed for downstream policy context",
                ),
                WeatherComponent(
                    name="liquidity_quality",
                    value=broad_context.liquidity_score,
                    contribution=Decimal("0"),
                    explanation="liquidity quality is exposed for downstream policy context",
                ),
                WeatherComponent(
                    name="headline_pressure",
                    value=headline_pressure,
                    contribution=((headline_pressure + Decimal("1")) / Decimal("2"))
                    * Decimal("0.10"),
                    explanation="headline sentiment contribution",
                ),
                WeatherComponent(
                    name="session_timing",
                    value=calendar.session_state.value,
                    contribution=Decimal("0"),
                    explanation="market session status for downstream policy context",
                ),
                WeatherComponent(
                    name="risk_posture",
                    value=broad_context.risk_on_score,
                    contribution=broad_context.risk_on_score * Decimal("0.45"),
                    explanation="provider broad risk posture contribution",
                ),
            ),
        )
