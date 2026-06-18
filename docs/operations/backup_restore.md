# Backup And Restore

## Backup

Managed production databases should use point-in-time recovery with cross-zone durability. Self-managed PostgreSQL can use:

```bash
ZULU_DATABASE_URL=postgresql://... ./scripts/backup_postgres.sh
```

Backups are written to `backups/` by default and must be moved to encrypted object storage. The script writes a SHA-256 checksum next to each dump.

## Restore Drill

Restore only into an isolated environment first:

```bash
ZULU_DATABASE_URL=postgresql://restore-target \
BACKUP_FILE=backups/zulu-postgres-YYYYMMDDTHHMMSSZ.dump \
./scripts/restore_postgres.sh
```

After restore:

1. Run migration validation.
2. Run API health/readiness checks.
3. Verify tenant isolation on restored data.
4. Verify audit events are present and immutable.
5. Reconcile outbox offsets before reopening consumers.

## Migration Strategy

- Validate migrations in CI with `npm run migrations:validate`.
- Use forward-fix for production data changes.
- Keep application rollback separate from data rollback.
- Do not downgrade production without an explicit restore plan and operator approval.

## Outbox Replay

1. Pause consumers.
2. Identify unprocessed `outbox_events`.
3. Confirm event idempotency keys.
4. Replay by tenant and aggregate order.
5. Mark processed only after downstream success.
6. Record audit/operator notes for replay windows.
