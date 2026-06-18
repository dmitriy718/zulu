# Deployment

Zulu release candidates deploy as separate web and Python service images with PostgreSQL and Redis supplied by local Compose or managed services.

## Local Docker Compose

```bash
npm run compose:config
docker compose -f infra/docker-compose.yml up --build
```

Local Compose starts PostgreSQL, Redis, API, web, signal-intelligence, execution, and learning services. Local credentials are development-only placeholders.

## Staging Template

Use `infra/deploy/docker-compose.staging.yml`.

Required environment:

- `ZULU_API_IMAGE`
- `ZULU_WEB_IMAGE`
- `ZULU_DATABASE_URL_FROM_SECRET_MANAGER`
- `ZULU_REDIS_URL_FROM_SECRET_MANAGER`
- `NEXT_PUBLIC_ZULU_API_BASE_URL`

Staging sets `ZULU_LIVE_TRADING_ENABLED=false`.

## Production Template

Use `infra/deploy/docker-compose.production.yml`.

Required environment:

- `ZULU_API_IMAGE`
- `ZULU_WEB_IMAGE`
- `ZULU_DATABASE_URL_FROM_SECRET_MANAGER`
- `ZULU_REDIS_URL_FROM_SECRET_MANAGER`
- `NEXT_PUBLIC_ZULU_API_BASE_URL`

Production defaults `ZULU_LIVE_TRADING_ENABLED=false`. Live activation requires the live-trading requirements in `docs/operations/live_trading_gates.md` and `docs/RELEASE_CANDIDATE_CHECKLIST.md`.

## Migrations

Before deployment:

```bash
npm run migrations:validate
```

Apply migrations from the release artifact:

```bash
uv run alembic -c infra/alembic.ini upgrade head
```

Rollback strategy is forward-fix by default. Alembic downgrades exist for local validation, but production rollback should restore the previous application image and apply a reviewed forward migration when data has changed.

## Rollback

1. Freeze new deploys.
2. Keep live trading disabled or activate the system kill switch.
3. Record an operator audit event.
4. Redeploy the previous API and web images.
5. Confirm `/healthz`, `/readyz`, web `/api/health`, queue consumers, and provider health.
6. If a migration introduced bad data, follow `docs/operations/backup_restore.md`.
7. Replay unprocessed outbox events after rollback validation.
