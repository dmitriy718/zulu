from datetime import UTC, datetime
from decimal import Decimal

import pytest
from zulu_signal_intelligence import MarketObservation, normalize_observation, service_health


def test_signal_intelligence_health_is_testable() -> None:
    assert service_health().service == "signal-intelligence"


def test_market_observation_normalization_uppercases_symbol() -> None:
    normalized = normalize_observation(
        MarketObservation(
            symbol="msft",
            observed_at=datetime.now(UTC),
            bid=Decimal("10.10"),
            ask=Decimal("10.20"),
            source="unit-test-fixture",
        )
    )

    assert normalized.symbol == "MSFT"


def test_market_observation_rejects_inverted_market() -> None:
    with pytest.raises(ValueError):
        normalize_observation(
            MarketObservation(
                symbol="MSFT",
                observed_at=datetime.now(UTC),
                bid=Decimal("10.20"),
                ask=Decimal("10.10"),
                source="unit-test-fixture",
            )
        )
