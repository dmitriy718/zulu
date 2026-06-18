# Provider Health

Provider health is part of the ingestion boundary, not a UI-only status check.

## Health States

Adapters report one of:

- `healthy`: provider path is available for configured mode.
- `degraded`: provider path is reachable but missing capabilities, delayed, or partially failing.
- `unavailable`: provider path cannot be used.

Local default development uses a deterministic fixture provider. Live provider clients are disabled unless explicitly configured.

## Capability Discovery

Every provider suite must expose capabilities before downstream services assume data availability. Capability checks cover stock data, options chains, options greeks, implied volatility, open interest, headlines, calendar data, index context, sector context, and volatility context.

Missing capability is not a reason to fabricate data. Policy and risk layers must see unavailable context explicitly.

## Failure Handling

Provider calls should use `ProviderExecutor`:

- Retry rate-limit failures with exponential backoff.
- Open the circuit after repeated failures.
- Return explicit errors when the circuit is open.
- Avoid silent fallback to old data.

Freshness checks still apply after a successful provider response.

## Operational Checks

For local verification:

```bash
uv run pytest services/signal-intelligence/tests
uv run ruff check services/signal-intelligence
uv run mypy services/signal-intelligence
```

For environment-gated provider clients:

- Confirm the provider is enabled only in the intended environment.
- Confirm credential references are present without logging secret values.
- Confirm health reports include mode and capability status.
- Confirm failures produce structured logs and do not expose raw credentials, account IDs, tokens, or sensitive host details.

## Incident Rules

Provider incidents should be recorded when:

- A live configured provider remains unavailable past the operational threshold.
- A provider returns stale or internally inconsistent market data.
- Options greeks, volume, or open interest disappear unexpectedly for a provider expected to support them.
- Market calendar/session status cannot be established during a trading-session workflow.

Incident records must include tenant scope when tenant-specific impact exists.
