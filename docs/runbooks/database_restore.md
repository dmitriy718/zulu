# Database Restore Runbook

1. Stop writers and queue consumers.
2. Confirm restore target and backup checksum.
3. Restore into isolated environment first.
4. Run migrations and anti-regression checks.
5. Verify tenant isolation, audit retention, outbox state, and reconciliation state.
6. Promote restored database only after operator approval.
7. Keep live trading disabled until reconciliation is complete.
