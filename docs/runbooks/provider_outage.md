# Provider Outage Runbook

1. Confirm provider health and circuit breaker state.
2. Check provider rate-limit metrics and stale-data alerts.
3. Pause affected ingestion jobs if stale data is entering the pipeline.
4. Confirm Signal Intelligence blocks stale or incomplete market context.
5. Notify operators and affected tenants if tenant-specific impact exists.
6. Keep Automation Station routing blocked for affected instruments until fresh data returns.
7. Record a system incident and resolution notes.
