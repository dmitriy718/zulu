from datetime import UTC, datetime
from decimal import Decimal

from zulu_contracts import AssetClass, CleanSignalV1
from zulu_risk import OrderIntent, PortfolioExposure, RiskContext, RiskGate, RiskLimits
from zulu_signal_intelligence.fixture_provider import FixtureMarketDataProvider
from zulu_signal_intelligence.ledger import InMemorySignalLedgerRepository
from zulu_signal_intelligence.pipeline import SignalIntelligencePipeline


def test_risk_gate_rejects_order_above_notional_limit() -> None:
    decision = RiskGate().evaluate(
        OrderIntent(symbol="MSFT", asset_class=AssetClass.STOCK, notional=Decimal("10001")),
        PortfolioExposure(symbol="MSFT", current_notional=Decimal("0")),
        RiskLimits(max_order_notional=Decimal("10000"), max_symbol_exposure=Decimal("25000")),
    )

    assert decision.approved is False
    assert "notional" in decision.reason


def test_risk_gate_approves_bounded_stock_or_option_order() -> None:
    decision = RiskGate().evaluate(
        OrderIntent(symbol="MSFT", asset_class=AssetClass.OPTION, notional=Decimal("5000")),
        PortfolioExposure(symbol="MSFT", current_notional=Decimal("1000")),
        RiskLimits(max_order_notional=Decimal("10000"), max_symbol_exposure=Decimal("25000")),
    )

    assert decision.approved is True


def _clean_signal() -> CleanSignalV1:
    now = datetime(2026, 6, 18, 14, 30, tzinfo=UTC)
    result = SignalIntelligencePipeline(
        provider=FixtureMarketDataProvider(now=now),
        repository=InMemorySignalLedgerRepository(),
    ).run(
        tenant_id="tenant_1",
        ticker="MSFT",
        user_id="user_1",
        actor_id="risk_test",
        correlation_id="risk_test",
        now=now,
    )
    assert result.accepted_signal is not None
    return result.accepted_signal


def test_risk_gate_approves_clean_signal_under_limits() -> None:
    signal = _clean_signal()
    decision = RiskGate().evaluate_signal(
        signal,
        RiskContext(
            tenant_id="tenant_1",
            user_id="user_1",
            now=datetime(2026, 6, 18, 14, 30, tzinfo=UTC),
            order_notional=Decimal("1000"),
            estimated_max_loss=Decimal("100"),
            requested_quantity=Decimal("10"),
        ),
        RiskLimits(max_order_notional=Decimal("10000"), max_symbol_exposure=Decimal("25000")),
    )

    assert decision.approved is True


def test_risk_gate_rejects_daily_loss_limit() -> None:
    signal = _clean_signal()
    decision = RiskGate().evaluate_signal(
        signal,
        RiskContext(
            tenant_id="tenant_1",
            user_id="user_1",
            now=datetime(2026, 6, 18, 14, 30, tzinfo=UTC),
            order_notional=Decimal("1000"),
            estimated_max_loss=Decimal("200"),
            daily_realized_loss=Decimal("900"),
            requested_quantity=Decimal("10"),
        ),
        RiskLimits(
            max_order_notional=Decimal("10000"),
            max_symbol_exposure=Decimal("25000"),
            max_daily_loss=Decimal("1000"),
        ),
    )

    assert decision.approved is False
    assert "daily loss" in decision.reason


def test_risk_gate_rejects_duplicate_signal_or_order() -> None:
    signal = _clean_signal()
    decision = RiskGate().evaluate_signal(
        signal,
        RiskContext(
            tenant_id="tenant_1",
            user_id="user_1",
            now=datetime(2026, 6, 18, 14, 30, tzinfo=UTC),
            order_notional=Decimal("1000"),
            estimated_max_loss=Decimal("100"),
            requested_quantity=Decimal("10"),
            duplicate_signal_or_order=True,
        ),
        RiskLimits(max_order_notional=Decimal("10000"), max_symbol_exposure=Decimal("25000")),
    )

    assert decision.approved is False
    assert "duplicate" in decision.reason
