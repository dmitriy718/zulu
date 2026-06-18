from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from zulu_contracts.domain import OptionType

from zulu_signal_intelligence.provider_models import (
    MarketSessionState,
    ProviderCapabilities,
    ProviderCapability,
    ProviderHealth,
    ProviderHealthState,
    ProviderProvenance,
    RawBroadMarketContext,
    RawHeadline,
    RawMarketCalendar,
    RawOptionContract,
    RawStockBar,
    RawStockQuote,
    RawStockTrade,
)


class FixtureMarketDataProvider:
    provider_name = "fixture-provider"

    def __init__(self, *, now: datetime | None = None) -> None:
        self.now = now or datetime(2026, 6, 18, 14, 30, tzinfo=UTC)

    def _provenance(self, record_id: str) -> ProviderProvenance:
        return ProviderProvenance(
            provider_name=self.provider_name,
            provider_mode="deterministic_fixture",
            provider_record_id=record_id,
            retrieved_at=self.now,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name=self.provider_name,
            capabilities=frozenset(
                {
                    ProviderCapability.STOCK_QUOTES,
                    ProviderCapability.STOCK_TRADES,
                    ProviderCapability.STOCK_BARS,
                    ProviderCapability.OPTIONS_CHAIN,
                    ProviderCapability.OPTIONS_QUOTES,
                    ProviderCapability.OPTIONS_TRADES,
                    ProviderCapability.OPTIONS_GREEKS,
                    ProviderCapability.OPTIONS_IMPLIED_VOLATILITY,
                    ProviderCapability.OPTIONS_OPEN_INTEREST,
                    ProviderCapability.HEADLINES,
                    ProviderCapability.MARKET_CALENDAR,
                    ProviderCapability.INDEX_CONTEXT,
                    ProviderCapability.SECTOR_CONTEXT,
                    ProviderCapability.VOLATILITY_CONTEXT,
                }
            ),
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name=self.provider_name,
            state=ProviderHealthState.HEALTHY,
            checked_at=self.now,
            detail="deterministic fixture provider is available",
        )

    def get_stock_quote(self, ticker: str) -> RawStockQuote:
        return RawStockQuote(
            ticker=ticker.upper(),
            bid=Decimal("100.10"),
            ask=Decimal("100.20"),
            last=Decimal("100.15"),
            volume=1500000,
            observed_at=self.now - timedelta(seconds=5),
            provenance=self._provenance(f"quote-{ticker.upper()}"),
        )

    def get_stock_trades(self, ticker: str) -> list[RawStockTrade]:
        return [
            RawStockTrade(
                ticker=ticker.upper(),
                price=Decimal("100.15"),
                size=100,
                traded_at=self.now - timedelta(seconds=4),
                provenance=self._provenance(f"trade-{ticker.upper()}-1"),
            )
        ]

    def get_stock_bars(self, ticker: str) -> list[RawStockBar]:
        return [
            RawStockBar(
                ticker=ticker.upper(),
                open=Decimal("98.50"),
                high=Decimal("101.00"),
                low=Decimal("97.80"),
                close=Decimal("100.15"),
                volume=1500000,
                vwap=Decimal("99.60"),
                started_at=self.now - timedelta(hours=1),
                ended_at=self.now,
                provenance=self._provenance(f"bar-{ticker.upper()}-1h"),
            ),
            RawStockBar(
                ticker=ticker.upper(),
                open=Decimal("96.00"),
                high=Decimal("101.00"),
                low=Decimal("95.50"),
                close=Decimal("100.15"),
                volume=1200000,
                vwap=Decimal("98.80"),
                started_at=self.now - timedelta(days=1),
                ended_at=self.now - timedelta(hours=1),
                provenance=self._provenance(f"bar-{ticker.upper()}-prev"),
            ),
        ]

    def get_options_chain(self, ticker: str) -> list[RawOptionContract]:
        return [self.get_option_contract(f"{ticker.upper()}270117C00100000")]

    def get_option_contract(self, option_symbol: str) -> RawOptionContract:
        return RawOptionContract(
            underlying_ticker=option_symbol[:4].strip().upper() or "MSFT",
            option_symbol=option_symbol.upper(),
            option_type=OptionType.CALL,
            strike=Decimal("100.00"),
            expiration_date=self.now + timedelta(days=213),
            multiplier=100,
            bid=Decimal("4.10"),
            ask=Decimal("4.25"),
            delta=Decimal("0.55"),
            gamma=Decimal("0.04"),
            theta=Decimal("-0.02"),
            vega=Decimal("0.12"),
            implied_volatility=Decimal("0.31"),
            open_interest=250,
            volume=75,
            observed_at=self.now - timedelta(seconds=20),
            provenance=self._provenance(f"option-{option_symbol.upper()}"),
        )

    def get_headlines(self, tickers: Sequence[str]) -> list[RawHeadline]:
        ticker = tickers[0].upper() if tickers else "MSFT"
        return [
            RawHeadline(
                provider_headline_id=f"headline-{ticker}-1",
                title=f"{ticker} reports steady enterprise demand in quarterly update",
                source_name="Fixture Newswire",
                url="https://fixture.local/news/steady-demand",
                published_at=self.now - timedelta(hours=2),
                tickers=[ticker],
                summary="Company update includes demand commentary and expense discipline.",
                provenance=self._provenance(f"headline-{ticker}-1"),
            ),
            RawHeadline(
                provider_headline_id=f"headline-{ticker}-1-duplicate",
                title=f"{ticker} reports steady enterprise demand in quarterly update",
                source_name="Fixture Newswire",
                url="https://fixture.local/news/steady-demand",
                published_at=self.now - timedelta(hours=2),
                tickers=[ticker],
                summary="Duplicate fixture headline with identical source URL.",
                provenance=self._provenance(f"headline-{ticker}-duplicate"),
            ),
        ]

    def get_market_calendar(self) -> RawMarketCalendar:
        return RawMarketCalendar(
            session_state=MarketSessionState.OPEN,
            session_date=self.now,
            next_close_at=self.now.replace(hour=20, minute=0, second=0, microsecond=0),
            next_open_at=self.now + timedelta(hours=18),
            provenance=self._provenance("calendar-session"),
        )

    def get_broad_market_context(self) -> RawBroadMarketContext:
        return RawBroadMarketContext(
            index_trend_score=Decimal("0.35"),
            sector_alignment_score=Decimal("0.20"),
            volatility_index_level=Decimal("17.50"),
            breadth_score=Decimal("0.58"),
            liquidity_score=Decimal("0.70"),
            risk_on_score=Decimal("0.62"),
            observed_at=self.now - timedelta(seconds=10),
            provenance=self._provenance("broad-context"),
        )
