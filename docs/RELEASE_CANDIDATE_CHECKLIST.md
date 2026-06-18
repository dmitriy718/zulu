# Release Candidate Checklist

## Complete

- Greenfield Zulu monorepo with Next.js web app, FastAPI API, Python service packages, contracts, policy, risk, execution, learning, and observability packages.
- Strict stocks/options domain contracts and database migration scaffold.
- Signal Intelligence pipeline with quality gates, durable outbox delivery, and accepted-signal invariants.
- Execution authority with PolicyGate, RiskGate, idempotency, audit, paper broker, live adapter hard gates, kill switches, and reconciliation incidents.
- Continuous learning with labels, replay, model registry, promotion gates, and bounded loop.
- Tenant-scoped API platform controls, auth abstraction, subscription gating, audit log, security middleware, and OpenAPI generation.
- Web mission-control interface with risk, uncertainty, decision trace, and fixture/API boundaries.
- Deployment templates, CI workflow, observability metrics, backup/restore scripts, runbooks, secret scanning, and final anti-regression script.

## Verified Commands

Use these release-candidate gates:

```bash
npm install
uv sync
npm run check:web
npm --workspace apps/web run test:e2e
npm run check:py
npm run migrations:validate
npm run compose:config
npm run security:audit
npm run security:secrets
npm run release:anti-regression
npm run release:verify
```

Container build and smoke where Docker resources allow:

```bash
npm run docker:build
docker compose -f infra/docker-compose.yml up --build
curl -fsS http://localhost:8000/readyz
curl -fsS http://localhost:3000/api/health
```

## Environment Assumptions

- Node.js 24.14.1 or newer compatible 24.x.
- npm 11.11.0 or newer compatible 11.x.
- Python 3.12.
- uv 0.10.12.
- Docker and Docker Compose for local container validation.
- PostgreSQL and Redis are either local Compose services or managed services.
- Production secrets are supplied by runtime environment or secret manager.

## Remaining Gaps

- API mission-control aggregation for the web app is not yet enabled; local UI uses explicit fixture mode.
- Real auth, billing, broker, and market-data providers are represented by abstractions or gated skeletons.
- Managed production infrastructure, alert routes, and dashboard provisioning are documented but not bound to a specific vendor.
- Production database backup should use managed point-in-time recovery when available.
- `npm audit --audit-level=high` passes, but npm still reports a moderate PostCSS advisory through the current Next.js dependency tree. No high-severity advisory is accepted for release.
- Local Compose API and web containers remain healthy; signal-intelligence, execution, and learning containers currently run health entrypoints and exit `0` after printing status rather than staying resident as workers.

## Launch Blockers

- No real secret manager integration configured.
- No production auth provider configured.
- No production market-data provider configured.
- No production broker transport configured.
- No production observability backend configured.
- No completed restore drill against a staging database.
- No approved live-trading risk/compliance review.

## Live-Trading Requirements Before Activation

Live trading remains disabled by default. Activation requires:

- Environment variable explicitly set for intended environment.
- Tenant subscription allows live automation.
- User has automation permission and explicit approval flow.
- PolicyGate approves.
- RiskGate approves.
- Broker adapter explicitly enabled.
- Credential reference exists in the secret manager.
- No active system, tenant, user, ticker, strategy, model, or broker kill switch.
- No critical active incident.
- Audit events and reconciliation paths verified.
- Paper-mode and shadow-mode validation accepted by operators.

## Rollback Process

1. Freeze rollout and assign operator owner.
2. Keep live trading disabled or activate system kill switch.
3. Redeploy previous API and web images.
4. Validate health, readiness, queue consumers, provider health, and final anti-regression gate.
5. Follow `docs/operations/backup_restore.md` if database restore is required.
6. Replay outbox events only after idempotency review.
7. Record audit/operator notes with image versions and verification results.
