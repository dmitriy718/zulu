# Zulu

Zulu is a greenfield stocks/options-only trading intelligence and automation platform.

The product has two modes:

- Signal Station: contextual signal review for stocks and options.
- Automation Station: approved signals can move through policy, risk, idempotency, audit, and execution controls.

Zulu is informational software. It does not promise trading outcomes and live trading is disabled by default.

## Architecture

- `apps/web`: Next.js App Router web app with health/status surfaces.
- `services/api`: FastAPI HTTP boundary with typed settings, structured logging, SQLAlchemy data models, health, and readiness endpoints.
- `services/signal-intelligence`: importable service package for market observation normalization and signal-intelligence health.
- `services/execution`: importable service package for broker-call prerequisites, paper adapter boundary, and execution health.
- `services/learning`: importable service package for model evaluation and promotion-gate health.
- `packages/contracts`: Pydantic contracts shared by Python services.
- `packages/policy`: PolicyGate logic.
- `packages/risk`: RiskGate and exposure checks.
- `packages/observability`: logging and audit helpers.
- `infra`: Docker Compose, Python service Dockerfile, and Alembic scaffold.
- `tests`: cross-service integration tests.
- `docs`: project principles, verification rules, safety posture, decisions, changelog, and research notes.

## Quickstart

Requirements verified for this foundation:

- Node.js `24.14.1`
- npm `11.11.0`
- Python `3.12`
- uv `0.10.12`
- Docker `29.5.3`
- Docker Compose `5.1.4`

Install dependencies:

```bash
npm install
uv sync
```

Run checks:

```bash
npm run release:verify
```

Layer-specific checks:

```bash
npm run check:web
npm run check:py
npm run compose:config
npm run migrations:validate
npm run release:anti-regression
```

Run locally without containers:

```bash
npm run dev:web
uv run python -m zulu_api
```

Health endpoints:

- Web: `http://localhost:3000/api/health`
- API health: `http://localhost:8000/healthz`
- API readiness: `http://localhost:8000/readyz`

## Local Docker Deployment

Validate Compose:

```bash
npm run compose:config
```

Start the local stack:

```bash
docker compose -f infra/docker-compose.yml up --build
```

This starts PostgreSQL, Redis, API, web, and service containers for signal intelligence, execution, and learning health checks.

## Staging And Production Deployment

Deployment templates:

- Staging: `infra/deploy/docker-compose.staging.yml`
- Production: `infra/deploy/docker-compose.production.yml`
- Environment examples: `infra/env/staging.env.example`, `infra/env/production.env.example`

Secrets must come from environment variables or a secret manager. Do not commit broker credentials, provider keys, payment keys, or session secrets.

Validate migrations before deployment:

```bash
npm run migrations:validate
uv run alembic -c infra/alembic.ini upgrade head
```

Rollback and deployment details live in `docs/operations/deployment.md`.

## Release Candidate Verification

Run:

```bash
npm run release:verify
npm --workspace apps/web run test:e2e
```

Optional local container smoke:

```bash
docker compose -f infra/docker-compose.yml up --build
curl -fsS http://localhost:8000/readyz
curl -fsS http://localhost:3000/api/health
```

The release checklist is `docs/RELEASE_CANDIDATE_CHECKLIST.md`.

## Safety Posture

- Stocks and options only.
- Live trading disabled by default.
- No broker adapter call without PolicyGate approval, RiskGate approval, an idempotency key, and an audit event.
- Accepted signals must reach a durable execution attempt or terminal rejection with a reason.
- Fixtures, simulations, and test doubles must be labeled as such.
- Broker credentials and secrets must never be committed, logged, or placed in `.env.example`.

## Development Notes

Use `.env.example` as the local configuration template. It contains safe placeholder values only.

Stack decisions and dependency verification live in `docs/research/current_stack_verification.md` and `docs/DECISIONS.md`.

Operational docs:

- `docs/operations/observability.md`
- `docs/operations/backup_restore.md`
- `docs/operations/security_checks.md`
- `docs/runbooks/`
