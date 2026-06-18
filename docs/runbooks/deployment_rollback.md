# Deployment Rollback Runbook

1. Freeze rollout and announce operator ownership.
2. Keep live trading disabled or activate system kill switch.
3. Redeploy previous API and web images.
4. Validate health/readiness, web health, queues, migrations, provider health, and anti-regression checks.
5. If database state changed, follow backup/restore process.
6. Replay outbox only after validating idempotency and downstream state.
7. Record rollback reason, image versions, and verification results.
