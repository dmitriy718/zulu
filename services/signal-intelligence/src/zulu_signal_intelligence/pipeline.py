from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256

from zulu_contracts import (
    AcceptedSignalTerminalState,
    AssetType,
    CleanSignalV1,
    EntryZone,
    PolicyStatus,
    PositionSizingHint,
    SignalDirection,
    StrategyCandidate,
    TakeProfitLevel,
)
from zulu_contracts.domain import DecisionTraceItem
from zulu_policy import PolicyInput

from zulu_signal_intelligence.context_service import MarketContextBundle, MarketContextService
from zulu_signal_intelligence.delivery import (
    AutomationStationRoutingHook,
    DeliveryResult,
    SignalStationDeliveryHandler,
)
from zulu_signal_intelligence.explanations import SignalExplanationGenerator
from zulu_signal_intelligence.ledger import DurableOutboxPublisher, SignalLedgerRepository
from zulu_signal_intelligence.providers import MarketContextProviderSuite
from zulu_signal_intelligence.quality import SignalQualityGate
from zulu_signal_intelligence.scoring import (
    BaselineCandidateScorer,
    CandidateScore,
    CandidateScorer,
)
from zulu_signal_intelligence.strategies import (
    StrategyContext,
    StrategyModule,
    default_strategy_modules,
)


class SignalPipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class RejectedCandidate:
    candidate: StrategyCandidate
    score: CandidateScore
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SignalPipelineResult:
    accepted_signal: CleanSignalV1 | None
    terminal_state: AcceptedSignalTerminalState | None
    delivery: DeliveryResult | None
    candidates: tuple[StrategyCandidate, ...]
    rejected_candidates: tuple[RejectedCandidate, ...]


class SignalIntelligencePipeline:
    def __init__(
        self,
        *,
        provider: MarketContextProviderSuite,
        repository: SignalLedgerRepository,
        strategies: tuple[StrategyModule, ...] | None = None,
        scorer: CandidateScorer | None = None,
        quality_gate: SignalQualityGate | None = None,
        explanation_generator: SignalExplanationGenerator | None = None,
    ) -> None:
        self.context_service = MarketContextService(provider)
        self.repository = repository
        self.outbox = DurableOutboxPublisher(repository)
        self.strategies = strategies or default_strategy_modules()
        self.scorer = scorer or BaselineCandidateScorer()
        self.quality_gate = quality_gate or SignalQualityGate()
        self.explanation_generator = explanation_generator or SignalExplanationGenerator()
        self.signal_station = SignalStationDeliveryHandler(
            repository=repository,
            outbox=self.outbox,
        )
        self.automation_station = AutomationStationRoutingHook(
            repository=repository,
            outbox=self.outbox,
        )

    def run(
        self,
        *,
        tenant_id: str,
        ticker: str,
        user_id: str,
        actor_id: str,
        correlation_id: str,
        now: datetime,
        route_to_automation: bool = False,
        option_symbol: str | None = None,
        policy_input: PolicyInput | None = None,
    ) -> SignalPipelineResult:
        context = self.context_service.build_context(
            tenant_id=tenant_id,
            ticker=ticker,
            option_symbol=option_symbol,
            now=now,
        )
        strategy_context = StrategyContext(
            tenant_id=tenant_id,
            ticker=ticker,
            feature_vector=context.feature_vector,
            generated_at=now,
            asset_type=AssetType.STOCK,
        )
        candidates = tuple(
            candidate
            for strategy in self.strategies
            if (candidate := strategy.generate(strategy_context)) is not None
        )
        rejected: list[RejectedCandidate] = []
        accepted_options: list[tuple[CleanSignalV1, StrategyCandidate, CandidateScore]] = []

        for candidate in candidates:
            score = self.scorer.score(candidate)
            signal = self._build_clean_signal(
                candidate=candidate,
                score=score,
                context=context,
                actor_id=actor_id,
                correlation_id=correlation_id,
                now=now,
            )
            gate_result = self.quality_gate.evaluate(signal, now=now)
            if gate_result.passed:
                accepted_options.append((signal, candidate, score))
            else:
                rejected.append(
                    RejectedCandidate(
                        candidate=candidate,
                        score=score,
                        reasons=gate_result.reasons,
                    )
                )

        if not accepted_options:
            return SignalPipelineResult(
                accepted_signal=None,
                terminal_state=None,
                delivery=None,
                candidates=candidates,
                rejected_candidates=tuple(rejected),
            )

        accepted_signal, accepted_candidate, _score = max(
            accepted_options,
            key=lambda item: item[0].quality_score,
        )
        self.repository.persist_accepted(
            signal=accepted_signal,
            candidate=accepted_candidate,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )
        if route_to_automation:
            policy = policy_input or PolicyInput(
                tenant_id=tenant_id,
                user_id=user_id,
                user_approved_signal=False,
                instrument_allowed=False,
                policy_version="policy-baseline-v1",
            )
            delivery = self.automation_station.route_for_policy_review(
                signal=accepted_signal,
                policy_input=policy,
                actor_id=actor_id,
                correlation_id=correlation_id,
            )
        else:
            delivery = self.signal_station.deliver(
                signal=accepted_signal,
                actor_id=actor_id,
                correlation_id=correlation_id,
            )
        if delivery.terminal_state is None:
            raise SignalPipelineError("accepted signal did not transition to terminal state")
        return SignalPipelineResult(
            accepted_signal=accepted_signal,
            terminal_state=delivery.terminal_state,
            delivery=delivery,
            candidates=candidates,
            rejected_candidates=tuple(rejected),
        )

    def _build_clean_signal(
        self,
        *,
        candidate: StrategyCandidate,
        score: CandidateScore,
        context: MarketContextBundle,
        actor_id: str,
        correlation_id: str,
        now: datetime,
    ) -> CleanSignalV1:
        entry_zone = _entry_zone(
            last=context.market_data.last,
            direction=candidate.direction,
        )
        stop_loss = _stop_loss(
            entry_zone=entry_zone,
            direction=candidate.direction,
            atr_fraction=candidate.feature_vector.feature_values[
                "canonical_v1.volatility.atr_proxy_fraction"
            ],
        )
        take_profit_levels = _take_profit_levels(
            entry_zone=entry_zone,
            direction=candidate.direction,
            stop_loss=stop_loss,
        )
        entry_trigger = _entry_trigger(candidate)
        explanation = self.explanation_generator.generate(
            candidate=candidate,
            score=score,
            context=context,
            entry_trigger=entry_trigger,
            stop_loss=stop_loss,
            take_profit_levels=take_profit_levels,
        )
        option_contract = (
            context.option_contract if candidate.asset_type == AssetType.OPTION else None
        )
        signal = CleanSignalV1(
            signal_id=_signal_id(candidate, score),
            tenant_id=candidate.tenant_id,
            asset_type=candidate.asset_type,
            ticker=candidate.ticker,
            option_contract=option_contract,
            direction=candidate.direction,
            timeframe=candidate.timeframe,
            entry_zone=entry_zone,
            entry_trigger=entry_trigger,
            stop_loss=stop_loss,
            take_profit_levels=take_profit_levels,
            position_sizing_hint=PositionSizingHint(
                max_risk_fraction=Decimal("0.005000"),
                notional_cap=Decimal("25000.00"),
                rationale="baseline sizing caps risk while signal history is still being learned",
            ),
            confidence_score=score.confidence_score,
            risk_score=score.risk_score,
            quality_score=score.quality_score,
            market_weather=context.market_weather,
            market_data_snapshot=context.market_data,
            headline_context=list(explanation.headline_context),
            technical_context=explanation.technical_context,
            volatility_context=explanation.volatility_context,
            liquidity_context=explanation.liquidity_context,
            upside_thesis=explanation.upside_thesis,
            downside_risk=explanation.downside_risk,
            invalidation_conditions=list(explanation.invalidation_conditions),
            model_manifest_id=score.model_manifest_id,
            feature_schema_version=candidate.feature_vector.schema_version,
            feature_hash=candidate.feature_vector.content_hash,
            feature_vector=candidate.feature_vector,
            policy_status=PolicyStatus.PENDING,
            created_at=now,
            expires_at=min(context.market_data.expires_at, now + timedelta(minutes=15)),
            decision_trace=[
                DecisionTraceItem(
                    stage="strategy_candidate",
                    decision=candidate.strategy_candidate_id,
                    reason=candidate.rationale,
                    at=now,
                ),
                DecisionTraceItem(
                    stage="scoring",
                    decision=score.model_mode,
                    reason=score.components[0].rationale,
                    at=now,
                ),
                DecisionTraceItem(
                    stage="quality_gate",
                    decision="pending_acceptance",
                    reason=(
                        f"candidate quality={score.quality_score}, confidence="
                        f"{score.confidence_score}, risk={score.risk_score}"
                    ),
                    at=now,
                ),
                DecisionTraceItem(
                    stage="explanation",
                    decision="attached",
                    reason=(
                        f"{explanation.confidence_explanation} "
                        f"{explanation.risk_explanation} {explanation.data_limitations}"
                    ),
                    at=now,
                ),
                DecisionTraceItem(
                    stage="actor",
                    decision=actor_id,
                    reason=f"correlation_id={correlation_id}",
                    at=now,
                ),
            ],
        )
        return signal


def _entry_zone(*, last: Decimal, direction: SignalDirection) -> EntryZone:
    spread = last * Decimal("0.002")
    if direction == SignalDirection.LONG:
        return EntryZone(
            lower=(last - spread).quantize(Decimal("0.000001")),
            upper=(last + spread).quantize(Decimal("0.000001")),
        )
    return EntryZone(
        lower=(last - spread).quantize(Decimal("0.000001")),
        upper=(last + spread).quantize(Decimal("0.000001")),
    )


def _stop_loss(
    *,
    entry_zone: EntryZone,
    direction: SignalDirection,
    atr_fraction: Decimal,
) -> Decimal:
    entry_mid = (entry_zone.lower + entry_zone.upper) / Decimal("2")
    risk_fraction = max(Decimal("0.006"), min(Decimal("0.025"), atr_fraction * Decimal("1.25")))
    if direction == SignalDirection.LONG:
        return (entry_mid * (Decimal("1") - risk_fraction)).quantize(Decimal("0.000001"))
    return (entry_mid * (Decimal("1") + risk_fraction)).quantize(Decimal("0.000001"))


def _take_profit_levels(
    *,
    entry_zone: EntryZone,
    direction: SignalDirection,
    stop_loss: Decimal,
) -> list[TakeProfitLevel]:
    entry_mid = (entry_zone.lower + entry_zone.upper) / Decimal("2")
    risk = entry_mid - stop_loss if direction == SignalDirection.LONG else stop_loss - entry_mid
    if direction == SignalDirection.LONG:
        first = entry_mid + (risk * Decimal("1.50"))
        second = entry_mid + (risk * Decimal("2.50"))
    else:
        first = entry_mid - (risk * Decimal("1.50"))
        second = entry_mid - (risk * Decimal("2.50"))
    return [
        TakeProfitLevel(
            label="tp1",
            price=first.quantize(Decimal("0.000001")),
            scale_out_fraction=Decimal("0.500000"),
        ),
        TakeProfitLevel(
            label="tp2",
            price=max(Decimal("0.000001"), second).quantize(Decimal("0.000001")),
            scale_out_fraction=Decimal("0.500000"),
        ),
    ]


def _entry_trigger(candidate: StrategyCandidate) -> str:
    setup_type = candidate.rationale.split(" candidate:", maxsplit=1)[0]
    return (
        f"{candidate.ticker} must confirm the {setup_type} setup inside the entry zone "
        "with current provider data still fresh."
    )


def _signal_id(candidate: StrategyCandidate, score: CandidateScore) -> str:
    digest = sha256(
        f"{candidate.strategy_candidate_id}:{candidate.feature_vector.content_hash}:"
        f"{score.confidence_score}:{score.risk_score}:{score.quality_score}".encode()
    ).hexdigest()
    return f"signal_{digest[:24]}"
