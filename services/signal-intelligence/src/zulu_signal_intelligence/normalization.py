from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class MarketObservation(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    observed_at: datetime
    bid: Decimal = Field(gt=Decimal("0"))
    ask: Decimal = Field(gt=Decimal("0"))
    source: str = Field(min_length=1)


def normalize_observation(observation: MarketObservation) -> MarketObservation:
    if observation.ask < observation.bid:
        raise ValueError("ask must be greater than or equal to bid")
    return MarketObservation(
        symbol=observation.symbol.upper(),
        observed_at=observation.observed_at,
        bid=observation.bid,
        ask=observation.ask,
        source=observation.source,
    )
