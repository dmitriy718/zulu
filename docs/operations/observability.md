# Observability

Zulu observability must be tenant-safe and risk-aware.

## Logs

- JSON structured logs through `zulu_observability`.
- Include request IDs and correlation IDs.
- Include tenant IDs only when authorized and necessary.
- Redact tokens, credentials, API keys, account IDs, private hostnames, private IPs, and sensitive stack traces.

## Metrics

Required metric names are declared in `zulu_observability.metrics`:

- `api.health`
- `api.latency_ms`
- `queue.depth`
- `signals.throughput`
- `signals.rejected`
- `policy.blocks`
- `risk.blocks`
- `broker.errors`
- `reconciliation.discrepancies`
- `provider.rate_limits`
- `model.status`
- `incidents.active`

Metrics labels must not contain secrets or broker account identifiers.

## Trace Propagation

Use `X-Request-ID` at the API boundary and carry the same correlation ID through service logs, audit events, outbox payloads, execution records, and reconciliation incidents.

## Health And Readiness

- API: `/healthz`, `/readyz`
- Web: `/api/health`
- Service packages expose testable health objects.
- Provider health appears through the provider interfaces and web mission-control data.

## Audit Retention

Audit events are immutable. Retain audit logs for at least seven years unless a stricter tenant, regulatory, or legal hold requirement applies. Archive older partitions to immutable storage with restore drills.
