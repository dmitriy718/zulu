from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from zulu_signal_intelligence.provider_models import (
    ProviderCapabilities,
    ProviderHealth,
    RawBroadMarketContext,
    RawHeadline,
    RawMarketCalendar,
    RawOptionContract,
    RawStockBar,
    RawStockQuote,
    RawStockTrade,
)


class ProviderConfigurationError(RuntimeError):
    pass


class StockMarketDataProvider(Protocol):
    def get_stock_quote(self, ticker: str) -> RawStockQuote: ...

    def get_stock_trades(self, ticker: str) -> Sequence[RawStockTrade]: ...

    def get_stock_bars(self, ticker: str) -> Sequence[RawStockBar]: ...


class OptionsMarketDataProvider(Protocol):
    def get_options_chain(self, ticker: str) -> Sequence[RawOptionContract]: ...

    def get_option_contract(self, option_symbol: str) -> RawOptionContract: ...


class HeadlineProvider(Protocol):
    def get_headlines(self, tickers: Sequence[str]) -> Sequence[RawHeadline]: ...


class MarketContextProvider(Protocol):
    def get_market_calendar(self) -> RawMarketCalendar: ...

    def get_broad_market_context(self) -> RawBroadMarketContext: ...


class MarketContextProviderSuite(
    StockMarketDataProvider,
    OptionsMarketDataProvider,
    HeadlineProvider,
    MarketContextProvider,
    Protocol,
):
    @property
    def provider_name(self) -> str: ...

    def capabilities(self) -> ProviderCapabilities: ...

    def health(self) -> ProviderHealth: ...


class EnvironmentGatedProviderClient:
    def __init__(self, *, provider_name: str, enabled: bool, api_key: str | None = None) -> None:
        self.provider_name = provider_name
        self.enabled = enabled
        self._api_key_present = bool(api_key)

    def ensure_enabled(self) -> None:
        if not self.enabled:
            raise ProviderConfigurationError(
                f"{self.provider_name} provider is disabled by environment configuration"
            )
        if not self._api_key_present:
            raise ProviderConfigurationError(
                f"{self.provider_name} provider requires a configured credential reference"
            )
