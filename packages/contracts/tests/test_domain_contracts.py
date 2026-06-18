from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from zulu_contracts import (
    AssetType,
    AuditEvent,
    CanonicalFeatureVectorV1,
    CleanSignalV1,
    EntryZone,
    HeadlineContextItem,
    MarketDataSnapshot,
    MarketWeatherSnapshot,
    OptionContractSnapshot,
    OptionType,
    OrderLifecycleEvent,
    OrderLifecycleStatus,
    PositionSizingHint,
    SignalDirection,
    TakeProfitLevel,
    Timeframe,
)
from zulu_contracts.domain import DecisionTraceItem, PolicyStatus


def feature_vector() -> CanonicalFeatureVectorV1:
    return CanonicalFeatureVectorV1(
        feature_vector_id="fv_1",
        tenant_id="tenant_1",
        ticker="MSFT",
        feature_values={"momentum_20d": Decimal("0.45")},
    )


def market_data(now: datetime) -> MarketDataSnapshot:
    return MarketDataSnapshot(
        snapshot_id="md_1",
        tenant_id="tenant_1",
        ticker="MSFT",
        bid=Decimal("100.00"),
        ask=Decimal("100.10"),
        last=Decimal("100.05"),
        volume=1000,
        source="unit-test-fixture",
        observed_at=now,
        expires_at=now + timedelta(minutes=5),
    )


def market_weather(now: datetime) -> MarketWeatherSnapshot:
    return MarketWeatherSnapshot(
        market_weather_id="mw_1",
        tenant_id="tenant_1",
        regime="balanced",
        volatility_regime="normal",
        breadth_score=Decimal("0.55"),
        risk_on_score=Decimal("0.50"),
        as_of=now,
        expires_at=now + timedelta(minutes=10),
    )


def valid_clean_signal(asset_type: AssetType = AssetType.STOCK) -> CleanSignalV1:
    now = datetime.now(UTC)
    vector = feature_vector()
    option_contract = None
    if asset_type == AssetType.OPTION:
        option_contract = OptionContractSnapshot(
            option_contract_id="opt_1",
            tenant_id="tenant_1",
            underlying_ticker="MSFT",
            option_symbol="MSFT270117C00100000",
            option_type=OptionType.CALL,
            strike=Decimal("100.00"),
            expiration_date=now + timedelta(days=30),
            multiplier=100,
            bid=Decimal("4.10"),
            ask=Decimal("4.30"),
            open_interest=100,
            volume=50,
            source="unit-test-fixture",
            observed_at=now,
        )
    return CleanSignalV1(
        signal_id="sig_1",
        tenant_id="tenant_1",
        asset_type=asset_type,
        ticker="MSFT",
        option_contract=option_contract,
        direction=SignalDirection.LONG,
        timeframe=Timeframe.SWING,
        entry_zone=EntryZone(lower=Decimal("99.50"), upper=Decimal("100.50")),
        entry_trigger="price closes above the entry zone with sufficient liquidity",
        stop_loss=Decimal("95.00"),
        take_profit_levels=[
            TakeProfitLevel(
                label="target_1", price=Decimal("110.00"), scale_out_fraction=Decimal("0.5")
            )
        ],
        position_sizing_hint=PositionSizingHint(
            max_risk_fraction=Decimal("0.01"),
            notional_cap=Decimal("10000.00"),
            rationale="bounded tenant risk fixture",
        ),
        confidence_score=Decimal("0.70"),
        risk_score=Decimal("0.30"),
        quality_score=Decimal("0.80"),
        market_weather=market_weather(now),
        market_data_snapshot=market_data(now),
        headline_context=[
            HeadlineContextItem(
                headline_event_id="headline_1", relevance="related earnings context"
            )
        ],
        technical_context="trend and support context",
        volatility_context="implied volatility context",
        liquidity_context="spread and volume context",
        upside_thesis="upside thesis",
        downside_risk="downside risk",
        invalidation_conditions=["break below stop"],
        model_manifest_id="model_1",
        feature_schema_version="canonical_features_v1",
        feature_hash=vector.content_hash,
        feature_vector=vector,
        policy_status=PolicyStatus.PENDING,
        created_at=now,
        expires_at=now + timedelta(hours=1),
        decision_trace=[
            DecisionTraceItem(
                stage="contract_validation", decision="accepted", reason="fixture is valid"
            )
        ],
    )


def test_clean_signal_serialization_roundtrip() -> None:
    signal = valid_clean_signal()

    payload = signal.model_dump_json()
    parsed = CleanSignalV1.model_validate_json(payload)

    assert parsed == signal


def test_option_signal_requires_option_contract_metadata() -> None:
    signal = valid_clean_signal()
    data = signal.model_dump()
    data["asset_type"] = AssetType.OPTION
    data["option_contract"] = None

    with pytest.raises(ValidationError, match="option contract"):
        CleanSignalV1.model_validate(data)


def test_signal_rejects_expired_market_data() -> None:
    signal = valid_clean_signal()
    data = signal.model_dump()
    data["market_data_snapshot"] = {
        **signal.market_data_snapshot.model_dump(),
        "observed_at": signal.created_at - timedelta(minutes=10),
        "expires_at": signal.created_at - timedelta(seconds=1),
    }

    with pytest.raises(ValidationError, match="expired market data"):
        CleanSignalV1.model_validate(data)


def test_signal_rejects_feature_hash_mismatch() -> None:
    signal = valid_clean_signal()
    data = signal.model_dump()
    data["feature_hash"] = "0" * 64

    with pytest.raises(ValidationError, match="feature hash"):
        CleanSignalV1.model_validate(data)


def test_empty_feature_vector_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least 1"):
        CanonicalFeatureVectorV1(
            feature_vector_id="fv_empty",
            tenant_id="tenant_1",
            ticker="MSFT",
            feature_values={},
        )


def test_naive_timestamps_are_rejected() -> None:
    data = market_data(datetime.now(UTC)).model_dump()
    data["observed_at"] = datetime.now()

    with pytest.raises(ValidationError, match="timezone-aware"):
        MarketDataSnapshot.model_validate(data)


def test_order_lifecycle_event_requires_reconciliation_or_incident() -> None:
    with pytest.raises(ValidationError, match="reconciliation"):
        OrderLifecycleEvent(
            order_lifecycle_event_id="ole_1",
            tenant_id="tenant_1",
            broker_order_request_id="bor_1",
            status=OrderLifecycleStatus.SUBMITTED,
        )


def test_audit_event_schema_is_generated() -> None:
    schema = AuditEvent.model_json_schema()

    assert schema["title"] == "AuditEvent"
    assert "audit_event_id" in schema["properties"]
