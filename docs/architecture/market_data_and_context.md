# Market Data And Context

Zulu normalizes raw provider payloads into strict contracts before any signal, policy, risk, learning, or execution logic can consume them.

## Provider Boundary

Provider adapters live behind interfaces in `services/signal-intelligence/src/zulu_signal_intelligence/providers.py`.

The required provider surfaces are:

- Stock quotes, trades, and bars.
- Options chain and contract metadata.
- Options quotes, trades, greeks, implied volatility, volume, and open interest where supported.
- Headlines, news, and catalyst events.
- Market calendar and session status.
- Broad index, sector, volatility, breadth, liquidity, and risk posture context.

Adapters expose provider health and capability discovery. Runtime code must branch from capabilities rather than assuming greeks, open interest, news, or calendar data exist.

## Provider Modes

`FixtureMarketDataProvider` is deterministic and safe for local development and tests. Its data is a labeled fixture, not live market data and not evidence of provider connectivity.

Environment-gated provider clients must call `ensure_enabled()` before any outbound provider request. Live or paid provider access requires explicit environment configuration and a credential reference. Secrets must come from the runtime environment or a secret manager, never from source code.

## Resilience

Provider calls run through `ProviderExecutor` when orchestrated by the context service. It provides:

- Exponential backoff for provider rate-limit responses.
- Circuit breaker protection after repeated failures.
- Explicit circuit-open failures instead of silent fallback to stale or fabricated data.

The fixture provider does not simulate live provider availability. It exists only to exercise normalization and feature behavior deterministically.

## Normalization

Normalizers transform raw provider models into shared contracts:

- `MarketDataSnapshot`
- `OptionContractSnapshot`
- `HeadlineEvent`
- `MarketWeatherSnapshot`
- `CanonicalFeatureVectorV1`

Every normalized snapshot carries source/provenance through the contract `source` field or deterministic identifiers derived from provider provenance.

Normalization rejects data that violates freshness, spread, liquidity, or required-count constraints. Missing option volume or open interest is rejected unless a later explicit policy rule handles that condition. Missing greeks or implied volatility are never converted to zero; feature generation marks availability separately and omits unavailable measured values.

## Canonical Features

`CanonicalFeatureVectorV1` generation uses stable feature names under `canonical_v1.*` and contract-provided stable hashing.

The v1 feature set includes:

- Trend and momentum.
- Volatility and ATR proxy context.
- Quote spread quality.
- Liquidity and relative volume.
- Gap/opening behavior.
- Support/resistance proximity.
- VWAP relationship.
- Index and sector alignment.
- Options liquidity and options data availability.
- Implied volatility context when available.
- Headline pressure.
- Market weather and regime flags.

The feature vector must never be empty. If a feature input is unavailable and cannot be safely represented, generation fails or marks explicit availability flags instead of inventing a numeric value.

## Market Weather

`MarketWeatherService` classifies broad conditions into a `MarketWeatherSnapshot` and exposes transparent components:

- Index trend.
- Volatility regime.
- Breadth and participation.
- Sector alignment.
- Liquidity quality.
- Headline risk.
- Session timing.
- Risk-on/risk-off posture.

The snapshot is intentionally compact for shared contracts. Component detail remains service-local context for audit, debugging, and future policy decisions.

## Headline Processing

Headline normalization deduplicates by provider URL when present, otherwise by source and title. Headlines without provider publication time or source name are not treated as verified provider metadata and are excluded from normalized `HeadlineEvent` output.

Headline classification is conservative. It tags broad categories such as earnings, guidance, analyst action, or general context and does not fabricate missing article content or claims.
