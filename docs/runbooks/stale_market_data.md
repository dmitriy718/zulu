# Stale Market Data Runbook

1. Check provider freshness and circuit breaker state.
2. Confirm stale snapshots are rejected by normalization.
3. Block new signals for affected tickers or providers.
4. Review outbox for signals created near the stale-data window.
5. Mark impacted accepted signals terminal with a reason if they cannot be delivered safely.
6. Record incident and tenant impact.
