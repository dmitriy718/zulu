# Reconciliation Mismatch Runbook

1. Pause affected broker route if mismatch is live or repeated.
2. Compare local lifecycle events with broker order status.
3. Check for missing fills, duplicate fills, stale pending orders, and orphan positions.
4. Create or confirm `SystemIncident` for unresolved discrepancies.
5. Use manual reconciliation only with operator ID, reason, timestamp, and audit context.
6. Replay outbox only after idempotency review.
