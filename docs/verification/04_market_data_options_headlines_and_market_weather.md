# Verification 04: Market Data, Options, Headlines, and Market Weather

Date: 2026-06-18

Result: NO-GO

Zulu has a real ingestion foundation: abstract provider protocols, deterministic fixture providers, strict raw provider models, normalizers, freshness/liquidity checks, headline deduplication, market-weather classification, and passing tests. This verification area is still NO-GO because stale stock bars can flow into canonical feature generation without freshness checks, and provider health/capability/outage behavior is not yet fail-closed enough for production signal decisions.

## Scope Inspected

- Project instructions: `AGENTS.md`
- Relevant docs:
  - `docs/architecture/market_data_and_context.md`
  - `docs/operations/provider_health.md`
  - `docs/architecture/contracts.md`
  - `docs/SAFETY_AND_COMPLIANCE.md`
  - `docs/VERIFY_EVERY_TASK.md`
  - `docs/research/nova_reference_lessons.md`
- Provider boundary and models:
  - `services/signal-intelligence/src/zulu_signal_intelligence/providers.py`
  - `services/signal-intelligence/src/zulu_signal_intelligence/provider_models.py`
  - `services/signal-intelligence/src/zulu_signal_intelligence/fixture_provider.py`
  - `services/signal-intelligence/src/zulu_signal_intelligence/resilience.py`
- Normalization, feature, weather, and pipeline paths:
  - `services/signal-intelligence/src/zulu_signal_intelligence/constraints.py`
  - `services/signal-intelligence/src/zulu_signal_intelligence/normalizers.py`
  - `services/signal-intelligence/src/zulu_signal_intelligence/context_service.py`
  - `services/signal-intelligence/src/zulu_signal_intelligence/features.py`
  - `services/signal-intelligence/src/zulu_signal_intelligence/weather.py`
  - `services/signal-intelligence/src/zulu_signal_intelligence/quality.py`
  - `services/signal-intelligence/src/zulu_signal_intelligence/pipeline.py`
- Contracts:
  - `packages/contracts/src/zulu_contracts/domain.py`
- Tests:
  - `services/signal-intelligence/tests/test_market_context_layer.py`
  - `services/signal-intelligence/tests/test_signal_pipeline.py`
  - `services/signal-intelligence/tests/test_health_and_normalization.py`
  - `packages/contracts/tests/test_domain_contracts.py`

Nova/reference repositories were not inspected.

## Command Map Used

Discovered from `package.json`, `apps/web/package.json`, `pyproject.toml`, and provider-health docs:

| Area | Command |
| --- | --- |
| Signal-intelligence tests | `uv run pytest services/signal-intelligence/tests` |
| Domain contract tests | `uv run pytest packages/contracts/tests/test_domain_contracts.py` |
| Python lint | `npm run lint:py` |
| Python typecheck | `npm run typecheck:py` |
| Full Python tests | `npm run test:py` |

Not run:

- `npm run check`, `npm run check:py`, and `npm run release:verify` because `check:py` invokes `npm run format:py`, which runs `ruff format .` and may mutate production code. This prompt allowed reports and temporary artifacts only.
- Frontend checks because this verification area targeted the backend ingestion/context layer and contract behavior, not UI rendering.
- Live provider checks because live/paid provider access must remain disabled by default.

## Commands Run And Results

| Command | Result | Evidence |
| --- | --- | --- |
| `uv run pytest services/signal-intelligence/tests` | PASS | `25 passed in 0.11s` |
| `uv run pytest packages/contracts/tests/test_domain_contracts.py` | PASS | `8 passed in 0.07s` |
| `npm run lint:py` | PASS | `ruff check .` returned `All checks passed!` |
| `npm run typecheck:py` | PASS | `mypy services packages tests` returned `Success: no issues found in 75 source files` |
| `npm run test:py` | PASS | `93 passed, 2 warnings in 1.18s` |

Transient `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, and `__pycache__` artifacts were removed after the run.

## Evidence-Backed Findings

### CRITICAL: Stale stock bars can influence canonical features and signals

Evidence:

- `MarketContextService.build_context` fetches stock bars through the provider at `services/signal-intelligence/src/zulu_signal_intelligence/context_service.py:64-66`.
- It passes those raw bars directly into `generate_canonical_feature_vector` at `services/signal-intelligence/src/zulu_signal_intelligence/context_service.py:98-109`.
- `generate_canonical_feature_vector` uses raw bars for trend, momentum, volatility, relative volume, gap, support/resistance, VWAP, and ATR features at `services/signal-intelligence/src/zulu_signal_intelligence/features.py:34-82`.
- `RawStockBar` validates timezone-aware timestamps, but no freshness window is enforced in `services/signal-intelligence/src/zulu_signal_intelligence/provider_models.py:115-130`.
- `constraints.reject_stale` exists at `services/signal-intelligence/src/zulu_signal_intelligence/constraints.py:23-27`, and tests cover stale stock quotes at `services/signal-intelligence/tests/test_market_context_layer.py:88-95`, but there is no equivalent stale-bar test.

Impact:

Stale or delayed bars can alter feature vectors and strategy candidates even when the current quote passes freshness checks. Per the verification requirements, stale data influencing a signal is Critical.

Required hardening:

- Normalize stock bars into a strict contract with `source`, `observed/started/ended` timestamps, expiry, and data-quality metadata.
- Reject or explicitly degrade stale bars before feature generation.
- Add tests proving stale bars cannot produce a `CanonicalFeatureVectorV1` or accepted signal.

### HIGH: Provider health and capabilities are observed but not enforced before data use

Evidence:

- Provider health and capabilities are read at `services/signal-intelligence/src/zulu_signal_intelligence/context_service.py:59-60`.
- The service proceeds to call quote, bars, headlines, calendar, broad context, and option contract providers at `services/signal-intelligence/src/zulu_signal_intelligence/context_service.py:61-91` without checking `provider_health.state` or required capabilities.
- Provider capability modeling exists in `services/signal-intelligence/src/zulu_signal_intelligence/provider_models.py:11-25` and provider protocols expose `capabilities()` at `services/signal-intelligence/src/zulu_signal_intelligence/providers.py:57`.
- Tests assert capabilities are exposed at `services/signal-intelligence/tests/test_market_context_layer.py:41-48`, but no tests prove missing capabilities fail closed or route data through policy/degraded status.

Impact:

A provider can report degraded/unavailable health or lack options/news/calendar capabilities while the context service still attempts to use its data path. Missing options greeks/open interest/news are not consistently represented as capability-driven degraded context before downstream decisions.

Required hardening:

- Add a capability/health preflight in `MarketContextService`.
- Fail closed for required capabilities, and explicitly mark optional capabilities as unavailable in context metadata.
- Add tests for unavailable providers, degraded providers, missing headlines, missing options greeks, missing open interest, and missing market calendar.

### HIGH: Provider outages do not produce a degraded context or incident path

Evidence:

- `ProviderExecutor.call` raises `ProviderCircuitOpenError` when the circuit is open at `services/signal-intelligence/src/zulu_signal_intelligence/resilience.py:70-71`.
- Generic provider exceptions record a circuit failure and are re-raised at `services/signal-intelligence/src/zulu_signal_intelligence/resilience.py:85-87`.
- Rate-limit retry and circuit-open tests exist at `services/signal-intelligence/tests/test_market_context_layer.py:192-221`.
- There is no `MarketContextBundle` state for degraded/unavailable context, no incident emission, and no test proving outage results become provider-health dashboard data or a durable incident.

Impact:

Outages do not silently return empty success, which is good. However, they also do not create the explicit degraded operational state required by the prompt. This weakens provider-health visibility and operator response.

Required hardening:

- Add a provider failure result model or incident path.
- Record provider outage/degraded state with tenant scope where relevant.
- Add tests proving provider failures cannot produce empty successful context and do produce visible degraded status.

### HIGH: Normalized snapshots lack explicit asset type and data-quality metadata

Evidence:

- `MarketDataSnapshot` includes prices, volume, source, observed/expiry/received timestamps at `packages/contracts/src/zulu_contracts/domain.py:180-187`.
- `OptionContractSnapshot` includes option metadata, bid/ask, greeks, open interest, volume, source, and observed timestamp at `packages/contracts/src/zulu_contracts/domain.py:203-222`.
- Neither snapshot contains an explicit `asset_type`.
- Neither snapshot contains structured data-quality metadata such as freshness state, spread state, liquidity state, provider capability status, delayed/realtime status, or degradation reasons.

Impact:

Downstream systems must infer quality from successful normalization rather than carrying auditable quality metadata forward. That makes it harder to explain degraded decisions, policy blocks, or provider limitations.

Required hardening:

- Add structured data-quality metadata to normalized market and option snapshots.
- Include explicit asset type or equivalent contract-level discriminators.
- Carry provider capability and delayed/realtime status into signal decision traces.

### HIGH: Options contract symbol validation is incomplete

Evidence:

- `RawOptionContract` requires underlying, option symbol, option type, strike, expiration, multiplier, bid/ask, volume/open interest, observed timestamp, and provenance at `services/signal-intelligence/src/zulu_signal_intelligence/provider_models.py:133-150`.
- It validates ask/bid ordering and expiration after observation at `services/signal-intelligence/src/zulu_signal_intelligence/provider_models.py:157-163`.
- `normalize_option_contract` rejects stale option data, wide spread, missing volume, and missing open interest at `services/signal-intelligence/src/zulu_signal_intelligence/normalizers.py:69-115`.
- The canonical `OptionContractSnapshot.option_symbol` only has length constraints at `packages/contracts/src/zulu_contracts/domain.py:207`.
- No code or test parses/validates an OCC/OSI option symbol, or checks that symbol, underlying, expiration, strike, and call/put agree.

Impact:

Malformed or internally inconsistent option symbols can be normalized if the provider object otherwise satisfies basic fields. That is not enough for production options execution/risk workflows.

Required hardening:

- Add an option-symbol parser/validator for supported option symbology.
- Verify symbol-underlying-expiration-strike-call/put consistency.
- Add negative tests for malformed symbols and inconsistent provider metadata.

### MEDIUM: Provider retries are bounded, but provider call timeouts are not implemented

Evidence:

- `RetryPolicy` bounds attempts and backoff parameters at `services/signal-intelligence/src/zulu_signal_intelligence/resilience.py:21-25`.
- `ProviderExecutor.call` retries rate-limit errors and opens the circuit at `services/signal-intelligence/src/zulu_signal_intelligence/resilience.py:63-94`.
- There is no timeout parameter or deadline enforcement around provider operations.

Impact:

A hanging provider call can block context generation. That can turn provider degradation into service latency or worker exhaustion.

Required hardening:

- Add per-operation timeout/deadline support.
- Add tests for timeout behavior and circuit breaker interaction.

### MEDIUM: Headline URL safety and summary-failure behavior are not enforced in ingestion

Evidence:

- `RawHeadline.url` is only an optional string with max length at `services/signal-intelligence/src/zulu_signal_intelligence/provider_models.py:166-174`.
- `normalize_headlines` stores the URL when provider metadata is complete at `services/signal-intelligence/src/zulu_signal_intelligence/normalizers.py:118-155`.
- Incomplete provider source/time metadata is excluded and duplicates are deduped, covered by `services/signal-intelligence/tests/test_market_context_layer.py:66-86`.
- There is no ingestion-layer validation of suspicious URL schemes/hosts and no explicit summary failure state.

Impact:

Zulu is not fetching headline URLs in this layer, so this is not currently an SSRF execution path. Still, unsafe URLs can be persisted/displayed, and summary failures are not represented as data-quality limitations.

Required hardening:

- Validate headline URLs before storing or exposing them.
- Record summary availability/failure as explicit headline quality metadata.
- Add tests for invalid URL schemes, internal/private hosts, duplicate URLs, missing source, missing published time, and absent summaries.

### LOW: No market-data cache layer exists to verify invalidation behavior

Evidence:

- Searches found no cache/TTL/invalidation implementation in `services/signal-intelligence/src`.
- The context path reads from the provider suite and normalizes data directly.

Impact:

There is no current cache serving old data as current, but there is also no cache invalidation design to verify when caching is added.

Required hardening:

- If a provider cache is added, require expiry-aware keys, tenant scope, provenance, and tests proving stale cache entries cannot be treated as current.

## Positive Evidence

- Provider interfaces are abstract and swappable via protocols in `services/signal-intelligence/src/zulu_signal_intelligence/providers.py:23-59`.
- A deterministic fixture provider exists and is used throughout tests: `services/signal-intelligence/src/zulu_signal_intelligence/fixture_provider.py:26-189`.
- Raw provider models are strict Pydantic models with forbidden extras at `services/signal-intelligence/src/zulu_signal_intelligence/provider_models.py:41-42`.
- Stock quote normalization rejects stale quotes, wide spreads, missing volume, and low volume at `services/signal-intelligence/src/zulu_signal_intelligence/normalizers.py:30-66`.
- Option normalization rejects stale option data, wide spreads, missing volume, missing open interest, and low liquidity at `services/signal-intelligence/src/zulu_signal_intelligence/normalizers.py:69-115`.
- Missing option greeks/implied volatility are represented as unavailable feature flags rather than zeroed values at `services/signal-intelligence/src/zulu_signal_intelligence/features.py:94-144`.
- Headline normalization excludes missing source/time metadata and deduplicates by URL/source/title at `services/signal-intelligence/src/zulu_signal_intelligence/normalizers.py:118-156`.
- Market weather uses explicit broad-market, calendar, and headline inputs, with transparent components in `services/signal-intelligence/src/zulu_signal_intelligence/weather.py:27-103`.
- Tests do not use live paid APIs; searches found no `httpx`, `requests`, `aiohttp`, `urllib`, socket, bearer token, or outbound request usage in signal-intelligence provider tests.

## Files Or Modules Requiring Hardening

- `services/signal-intelligence/src/zulu_signal_intelligence/context_service.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/features.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/provider_models.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/providers.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/resilience.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/normalizers.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/weather.py`
- `packages/contracts/src/zulu_contracts/domain.py`
- `services/signal-intelligence/tests/test_market_context_layer.py`
- `services/signal-intelligence/tests/test_signal_pipeline.py`

## Tests Missing Or Weak

- No stale stock bar rejection test.
- No stale market calendar/session status test.
- No degraded/unavailable provider health preflight test.
- No missing provider capability test for required stock, options, headline, calendar, or broad-market context.
- No provider timeout test.
- No test proving provider outage creates degraded health/incidents instead of only raising an exception.
- No option symbol parser/metadata consistency tests.
- No headline suspicious URL test.
- No explicit data-quality metadata tests for normalized snapshots.
- No cache invalidation tests because no market-data cache layer exists.

## What Was Not Verified And Why

- Live provider connectivity was not verified because live/paid providers must be disabled by default and no live provider client is configured.
- Provider dashboard persistence/incident integration was not verified because the current signal-intelligence context layer does not emit durable provider incidents.
- Cache invalidation was not verified because no ingestion cache implementation exists.
- Full aggregate `npm run check` was not run because it invokes `ruff format .` through `check:py`, which may mutate production code and violates this prompt's report-only policy.

## Recommended Matching Hardening Prompt

```text
Read AGENTS.md, docs/architecture/market_data_and_context.md, docs/operations/provider_health.md, docs/architecture/contracts.md, docs/architecture/signal_intelligence.md, and docs/verification/04_market_data_options_headlines_and_market_weather.md first.

Objective:
Harden Zulu's market data, options, headline, and weather context layer so verification 04 can move from NO-GO to GO.

Requirements:
1. Add normalized stock bar contracts or equivalent strict models with source, timestamps, expiry, asset type, and data-quality metadata.
2. Reject or explicitly degrade stale stock bars before canonical feature generation.
3. Add provider health/capability preflight checks in MarketContextService and fail closed for required capabilities.
4. Add explicit degraded provider context or incident output for provider outages, rate limits, circuit-open state, and missing capabilities.
5. Add bounded provider call timeouts.
6. Add robust option symbol parsing and consistency checks for underlying, expiration, strike, and call/put.
7. Add headline URL safety validation and summary-availability/failure metadata.
8. Add data-quality metadata to market data, option, headline, and weather contracts where appropriate.
9. Add tests for stale bars, stale calendar, provider unavailable/degraded state, missing capabilities, timeout behavior, option symbol mismatch, suspicious headline URLs, and no stale data reaching signal decisions.

Verification:
Run the discovered signal-intelligence tests, contract tests, Python lint/typecheck/tests, and a fixture integration test from provider context to rejected/accepted signal. Do not fabricate live provider results.
```

## Final Determination

NO-GO for verification area 04.

Reason: quote/options/headline/weather basics are implemented and tested, but stale stock bars can still influence feature generation and therefore signals. Provider health/capability/outage handling also lacks the explicit degraded/fail-closed behavior required for production market context.
