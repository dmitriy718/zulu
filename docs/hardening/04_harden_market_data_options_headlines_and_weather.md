# Hardening 04: Market Data, Options, Headlines, and Weather

Date: 2026-06-18

Result: PARTIAL

This hardening pass closes the release-blocking Verification 04 paths for stale stock bars reaching feature generation, missing option symbol consistency validation, and provider outages silently succeeding. It also adds cache TTL behavior, provider health/capability fail-closed preflight, headline URL safety, explicit data-quality context metadata, and tests for the new behavior.

The result is PARTIAL because durable provider incident persistence and contract-level asset/data-quality fields on every normalized object remain open follow-up work.

## Findings Addressed

- CRITICAL: stale stock bars could influence canonical features and signals.
- HIGH: provider health and capabilities were observed but not enforced before data use.
- HIGH: provider outages did not produce explicit degraded/failure behavior.
- HIGH: options contract symbol validation was incomplete.
- MEDIUM: provider timeout behavior was not represented.
- MEDIUM: headline URL safety and summary-unavailable state were not represented.
- LOW: no cache TTL behavior existed for provider responses.

## Files Changed

- `services/signal-intelligence/src/zulu_signal_intelligence/cache.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/constraints.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/context_service.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/fixture_provider.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/normalizers.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/provider_models.py`
- `services/signal-intelligence/src/zulu_signal_intelligence/resilience.py`
- `services/signal-intelligence/tests/test_market_context_layer.py`
- `services/signal-intelligence/tests/test_signal_pipeline.py`
- `packages/contracts/tests/test_domain_contracts.py`
- `services/execution/tests/test_adapter_safety.py`
- `docs/hardening/04_harden_market_data_options_headlines_and_weather.md`

## Implementation Summary

- Added `DataQualityStatus` and `DataQualityMetadata` strict provider-side models.
- Added stock bar internal validation for timestamp order, high/low consistency, and open/close/VWAP range consistency.
- Added `normalize_stock_bars`, which requires at least two bars, rejects duplicate provider records and duplicate bar end timestamps, requires volume/VWAP, sorts out-of-order bars deterministically, and rejects stale latest bars before feature generation.
- Wired `MarketContextService` to normalize bars before calling `generate_canonical_feature_vector`.
- Added provider health and capability preflight. The context service now fails closed when the provider is degraded/unavailable or required capabilities are missing.
- Added `MarketContextUnavailableError` so provider failures become explicit degraded/unavailable failures rather than empty success.
- Added `ProviderResponseCache` with tenant/provider/operation/instrument keys and TTL expiration.
- Added bounded elapsed-time timeout detection to `ProviderExecutor` through `RetryPolicy.timeout_seconds`.
- Added OCC-style option symbol parsing and consistency checks for underlying, expiration, call/put, and strike.
- Added headline URL safety checks for URL scheme and private/loopback/link-local/reserved/multicast IP targets.
- Added explicit `summary_present` / `summary_unavailable` state in conservative catalyst summaries.
- Corrected fixture/test option symbols from `MSFT260117C00100000` to `MSFT270117C00100000` so the encoded expiration matches the fixture's 2027 contract date.

## Tests Added Or Updated

- Stale stock bars are rejected before feature generation.
- Context generation rejects stale bars before a signal context can be built.
- Stock bars are sorted when out of order and duplicate bars are rejected.
- Option contract symbol metadata mismatch is rejected.
- Provider unavailable health fails closed.
- Missing provider capabilities fail closed.
- Provider outage raises explicit `MarketContextUnavailableError`.
- Provider response cache uses tenant/provider/operation/instrument keys and TTL expiry.
- Provider timeout behavior opens the timeout error path.
- Headline URL safety rejects unsafe local IP URLs.
- Summary-unavailable state is represented in catalyst summaries.
- Existing fixture option-symbol references were updated to remain internally consistent with stricter validation.

## Commands Run And Results

| Command | Result | Evidence |
| --- | --- | --- |
| `uv run pytest services/signal-intelligence/tests` | FAIL, then PASS | First run exposed inconsistent fixture option expiration after adding OCC validation. After fixing fixture/test symbols, `34 passed in 0.12s`. |
| `npm run lint:py` | FAIL, then PASS | First run found import ordering, long lines, and Python 3.12 generic style. After fixes, `All checks passed!`. |
| `npm run typecheck:py` | FAIL, then PASS | First run found an invalid `ParamSpec` wrapper. After simplifying the wrapper, `Success: no issues found in 76 source files`. |
| `uv run pytest packages/contracts/tests/test_domain_contracts.py services/signal-intelligence/tests tests/integration/test_signal_pipeline_integration.py` | FAIL | `tests/integration/test_signal_pipeline_integration.py` does not exist in this repo. The actual integration test present is `tests/integration/test_execution_gate_integration.py`. |
| `uv run pytest packages/contracts/tests/test_domain_contracts.py services/signal-intelligence/tests tests/integration/test_execution_gate_integration.py` | PASS | `43 passed in 0.13s`. |
| `npm run test:py` | PASS | `102 passed, 2 warnings in 1.73s`. |
| `npm run release:anti-regression` | PASS | Passed all final anti-regression probes, including provider stale data blocks signals. |

Transient `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, and `__pycache__` artifacts were removed after verification.

## Findings Closed With Evidence

### Closed: stale stock bars can no longer reach feature generation unvalidated

Evidence:

- `normalize_stock_bars` rejects stale latest bars, missing volume, missing VWAP, duplicate provider records, and duplicate bar timestamps.
- `MarketContextService.build_context` now calls `normalize_stock_bars` before `generate_canonical_feature_vector`.
- Tests:
  - `test_stale_stock_bars_are_rejected_before_feature_generation`
  - `test_context_service_rejects_stale_bars_before_signal_context`
  - `test_stock_bars_are_sorted_and_duplicates_are_rejected`

### Closed: provider health/capability failures now fail closed

Evidence:

- `MarketContextService._require_provider_ready` blocks degraded/unavailable health and missing required capabilities.
- Tests:
  - `test_provider_health_and_capability_preflight_fails_closed`

### Closed: provider outages no longer look like empty success

Evidence:

- Provider-call failures are wrapped in `MarketContextUnavailableError` with tenant/provider/operation context.
- Test:
  - `test_provider_outage_is_explicit_degraded_failure_not_empty_success`

### Closed: options metadata validation is materially stronger

Evidence:

- `normalize_option_contract` now validates supported OCC-style symbol format and checks underlying, expiration, call/put, and strike against provider metadata before creating `OptionContractSnapshot`.
- Test:
  - `test_option_contract_symbol_must_match_provider_metadata`

### Closed: duplicate/out-of-order bar handling exists

Evidence:

- Bars are sorted descending by `ended_at`; duplicate provider records or duplicate end timestamps are rejected.
- Test:
  - `test_stock_bars_are_sorted_and_duplicates_are_rejected`

### Closed: headline URL safety and summary state are represented

Evidence:

- `normalize_headlines` skips unsafe headline URLs.
- `is_safe_headline_url` rejects non-HTTP(S), localhost, private, loopback, link-local, reserved, and multicast IP hosts.
- `conservative_catalyst_summary` includes `summary_present` or `summary_unavailable`.
- Test:
  - `test_headline_url_safety_and_summary_state_are_explicit`

### Closed: cache TTL behavior exists and cannot serve expired entries as current

Evidence:

- `ProviderResponseCache` keys include tenant, provider, operation, and instrument.
- Expired cache entries are evicted and treated as misses.
- Test:
  - `test_provider_response_cache_uses_tenant_provider_operation_and_ttl`

## Findings Still Open

- MEDIUM: data-quality metadata is carried on `MarketContextBundle`, but `MarketDataSnapshot`, `OptionContractSnapshot`, `HeadlineEvent`, and `MarketWeatherSnapshot` do not yet have canonical contract-level data-quality fields or explicit asset-type discriminators.
- MEDIUM: provider timeout detection is elapsed-time based after the provider operation returns. Real live clients still need HTTP/client-level connect/read/write timeouts so truly hanging I/O is bounded at the transport layer.
- MEDIUM: provider outage/degraded state is explicit in the context service, but not yet persisted as a durable `SystemIncident` or provider-health event.
- LOW: `ProviderResponseCache` is in-memory only. That is acceptable for local deterministic tests, but production deployments need a Redis-backed or process-safe cache if caching is required across workers.

## Risks Introduced Or Consciously Avoided

- The new OCC-style option validation intentionally rejects internally inconsistent fixture/provider data. This required updating stale test symbols to a valid 2027 symbol instead of weakening validation.
- Provider health `degraded` currently fails closed for context generation. This is conservative and may block signals during partial provider impairment until a policy-aware degraded-mode path is designed.
- The headline URL safety check does not fetch URLs. It only prevents obviously unsafe URLs from entering normalized headline events.
- Cache TTL is short by default and still followed by normalization freshness checks, so cached provider objects cannot bypass stale-data validation.
- No live provider behavior was simulated or claimed.

## Exact Verification Prompt To Rerun

```text
Read AGENTS.md, docs/architecture/market_data_and_context.md, docs/operations/provider_health.md, docs/architecture/contracts.md, docs/SAFETY_AND_COMPLIANCE.md, docs/verification/04_market_data_options_headlines_and_market_weather.md, and docs/hardening/04_harden_market_data_options_headlines_and_weather.md first.

Objective:
Rerun Verification 04 after hardening and determine whether market data, options data, headlines, and weather context are traceable, stale-safe, provider-aware, and testable.

Commands to discover and run from repo files:
- signal-intelligence provider/context tests,
- contract tests,
- stale-data and options validation tests,
- headline safety tests,
- cache tests,
- signal pipeline regression tests,
- Python lint,
- Python typecheck,
- full Python tests,
- final anti-regression script where applicable.

Report:
Create or update docs/verification/04_market_data_options_headlines_and_market_weather.md with current evidence, remaining findings, and a GO / PARTIAL / NO-GO result. Do not use live provider data or fabricate results.
```
