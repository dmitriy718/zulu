from datetime import UTC, datetime

from zulu_contracts import AssetType, CleanSignalV1
from zulu_policy import (
    ExecutionEnvironment,
    MarketSessionStatus,
    PolicyContext,
    PolicyGate,
    PolicyInput,
    SubscriptionMode,
)
from zulu_signal_intelligence.fixture_provider import FixtureMarketDataProvider
from zulu_signal_intelligence.ledger import InMemorySignalLedgerRepository
from zulu_signal_intelligence.pipeline import SignalIntelligencePipeline


def test_policy_gate_fails_closed_without_user_approval() -> None:
    decision = PolicyGate().evaluate(
        PolicyInput(
            tenant_id="tenant_1",
            user_id="user_1",
            user_approved_signal=False,
            instrument_allowed=True,
            policy_version="policy-1",
        )
    )

    assert decision.approved is False
    assert "approval" in decision.reason


def test_policy_gate_approves_explicit_allowed_signal() -> None:
    decision = PolicyGate().evaluate(
        PolicyInput(
            tenant_id="tenant_1",
            user_id="user_1",
            user_approved_signal=True,
            instrument_allowed=True,
            policy_version="policy-1",
        )
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
        actor_id="policy_test",
        correlation_id="policy_test",
        now=now,
    )
    assert result.accepted_signal is not None
    return result.accepted_signal


def test_policy_gate_approves_rich_paper_context() -> None:
    signal = _clean_signal()
    decision = PolicyGate().evaluate(
        PolicyContext(
            tenant_id="tenant_1",
            user_id="user_1",
            user_approved_signal=True,
            instrument_allowed=True,
            policy_version="policy-2",
            subscription_mode=SubscriptionMode.PAPER_AUTOMATION,
            user_automation_permission=True,
            environment=ExecutionEnvironment.PAPER,
            supported_asset_types=frozenset({AssetType.STOCK, AssetType.OPTION}),
            now=datetime(2026, 6, 18, 14, 30, tzinfo=UTC),
        ),
        signal,
    )

    assert decision.approved is True
    assert decision.action == "routed"


def test_policy_gate_rejects_restricted_ticker() -> None:
    signal = _clean_signal()
    decision = PolicyGate().evaluate(
        PolicyContext(
            tenant_id="tenant_1",
            user_id="user_1",
            user_approved_signal=True,
            instrument_allowed=True,
            policy_version="policy-2",
            subscription_mode=SubscriptionMode.PAPER_AUTOMATION,
            user_automation_permission=True,
            supported_asset_types=frozenset({AssetType.STOCK}),
            restricted_tickers=frozenset({"MSFT"}),
            now=datetime(2026, 6, 18, 14, 30, tzinfo=UTC),
        ),
        signal,
    )

    assert decision.approved is False
    assert "restricted" in decision.reason


def test_policy_gate_rejects_closed_market_session() -> None:
    signal = _clean_signal()
    decision = PolicyGate().evaluate(
        PolicyContext(
            tenant_id="tenant_1",
            user_id="user_1",
            user_approved_signal=True,
            instrument_allowed=True,
            policy_version="policy-2",
            subscription_mode=SubscriptionMode.PAPER_AUTOMATION,
            user_automation_permission=True,
            supported_asset_types=frozenset({AssetType.STOCK}),
            market_session_status=MarketSessionStatus.CLOSED,
            now=datetime(2026, 6, 18, 14, 30, tzinfo=UTC),
        ),
        signal,
    )

    assert decision.approved is False
    assert "session" in decision.reason


def test_policy_gate_rejects_live_without_explicit_live_enablement() -> None:
    signal = _clean_signal()
    decision = PolicyGate().evaluate(
        PolicyContext(
            tenant_id="tenant_1",
            user_id="user_1",
            user_approved_signal=True,
            instrument_allowed=True,
            policy_version="policy-2",
            subscription_mode=SubscriptionMode.LIVE_AUTOMATION,
            user_automation_permission=True,
            environment=ExecutionEnvironment.LIVE,
            live_trading_enabled=False,
            supported_asset_types=frozenset({AssetType.STOCK}),
            now=datetime(2026, 6, 18, 14, 30, tzinfo=UTC),
        ),
        signal,
    )

    assert decision.approved is False
    assert "live trading" in decision.reason
