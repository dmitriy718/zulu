# Build, Install, And Command Reproducibility Verification

Date: 2026-06-18

Result: PARTIAL

## Scope Inspected

- Root instructions: `AGENTS.md`.
- Setup and verification docs: `README.md`, `docs/VERIFY_EVERY_TASK.md`, `docs/RELEASE_CANDIDATE_CHECKLIST.md`, `docs/operations/deployment.md`, `docs/operations/backup_restore.md`, `docs/operations/security_checks.md`, and prior verification report `docs/verification/01_greenfield_integrity_and_instruction_loading.md`.
- Frontend/workspace package files: `package.json`, `apps/web/package.json`, `package-lock.json`, `apps/web/Dockerfile`.
- Python environment files: `pyproject.toml`, `uv.lock`, `infra/Dockerfile.python`, `infra/alembic.ini`.
- CI and deployment files: `.github/workflows/ci.yml`, `infra/docker-compose.yml`, `infra/deploy/docker-compose.staging.yml`, `infra/deploy/docker-compose.production.yml`.
- Environment templates: `.env.example`, `infra/env/staging.env.example`, `infra/env/production.env.example`.
- Build/test/deploy scripts: `scripts/secret_scan.py`, `scripts/final_anti_regression.py`, `infra/scripts/validate_migrations.py`, `scripts/backup_postgres.sh`, `scripts/restore_postgres.sh`.
- Runtime surfaces relevant to fixture/API mode: `apps/web/lib/routeGuards.ts`, `apps/web/lib/apiClient.ts`, `apps/web/app/api/health/route.ts`, `services/api/src/zulu_api/main.py`, `services/api/src/zulu_api/platform.py`.

## Command Map Used

Discovered from root `package.json`:

- `npm run dev:web`
- `npm run build:web`
- `npm run lint:web`
- `npm run typecheck:web`
- `npm run test:web`
- `npm run format:web`
- `npm run check:web`
- `npm run lint:py`
- `npm run format:py`
- `npm run typecheck:py`
- `npm run test:py`
- `npm run check:py`
- `npm run migrations:validate`
- `npm run compose:config`
- `npm run docker:build`
- `npm run security:audit`
- `npm run security:secrets`
- `npm run release:anti-regression`
- `npm run release:verify`
- `npm run check`

Discovered from `apps/web/package.json`:

- `npm --workspace apps/web run dev`
- `npm --workspace apps/web run build`
- `npm --workspace apps/web run start`
- `npm --workspace apps/web run lint`
- `npm --workspace apps/web run typecheck`
- `npm --workspace apps/web run test`
- `npm --workspace apps/web run test:e2e`
- `npm --workspace apps/web run format`
- `npm --workspace apps/web run check`

Discovered from CI:

- `npm ci`
- `uv sync --locked`
- `npm run check:web`
- `npm run check:py`
- `npm run migrations:validate`
- `npm run compose:config`
- `npm run docker:build`
- `npm run security:audit`
- `npm run security:secrets`
- `npm run release:anti-regression`

Discovered from docs:

- Local install: `npm install`, `uv sync`.
- Release verification: `npm run release:verify`, `npm --workspace apps/web run test:e2e`.
- Optional container smoke: `docker compose -f infra/docker-compose.yml up --build`, `curl -fsS http://localhost:8000/readyz`, `curl -fsS http://localhost:3000/api/health`.
- Migration command: `uv run alembic -c infra/alembic.ini upgrade head`.
- Backup/restore scripts require `ZULU_DATABASE_URL`, `BACKUP_DIR`, and `BACKUP_FILE`.

## Commands Run And Results

| Command | Result | Evidence |
| --- | --- | --- |
| `node --version; npm --version; python3 --version; uv --version; docker --version; docker compose version` | PASS | Node `v24.14.1`, npm `11.11.0`, Python `3.12.3`, uv `0.10.12`, Docker `29.5.3`, Docker Compose `5.1.4`. |
| `test -f package-lock.json`; `test -f uv.lock` | PASS | Both lockfiles exist. |
| `npm ci` | PASS | Installed 485 packages from lockfile. npm reported 2 moderate advisories, no high-level install failure. |
| `uv sync --locked` | PASS | Resolved and checked locked Python packages. |
| `npm run check:web` | PASS | Prettier check, ESLint, TypeScript, Vitest, and Next production build passed. Web tests: 3 files, 9 tests passed. |
| `npm --workspace apps/web run test:e2e` | PASS | Playwright route smoke passed: 10 tests. |
| `npm run lint:py` | PASS | `ruff check .` passed. |
| `npm run typecheck:py` | PASS | Mypy passed: no issues in 75 source files. |
| `npm run test:py` | PASS | Pytest passed: 93 tests, 2 deprecation warnings. |
| `npm run migrations:validate` | PASS | Alembic downgrade, clean upgrade, expected table/trigger validation, and downgrade passed against PostgreSQL. |
| `npm run compose:config` | PASS | Docker Compose config rendered successfully with Zulu service names and env vars. |
| `npm run security:audit` | PASS at configured threshold | `npm audit --audit-level=high` exited 0; `uv pip check` found all installed packages compatible. npm still reports the known moderate PostCSS advisory through Next.js. |
| `npm run security:secrets` | PASS | Secret scan passed. |
| `npm run release:anti-regression` | PASS | All listed anti-regression checks passed, including live disabled by default, tenant isolation, idempotency, stop-loss, PolicyGate/RiskGate, kill switches, stale data, and reconciliation incidents. |
| `npm run docker:build` | PASS | Docker Compose built API, web, signal-intelligence, execution, and learning images. Web production build inside Docker passed. |
| `docker compose -f infra/docker-compose.yml up -d` | PASS | API, web, Postgres, and Redis started; service health entrypoint containers launched. |
| `curl -fsS http://127.0.0.1:8000/readyz` | PASS | API readiness returned `status:"ok"` with live trading disabled, database configured, Redis configured. |
| `curl -fsS http://127.0.0.1:3000/api/health` | PASS | Web health returned `status:"ok"` and `liveTradingEnabled:false`. |
| `docker compose -f infra/docker-compose.yml ps -a` | PASS with limitation | API/web/Postgres/Redis healthy. Signal-intelligence, execution, and learning containers exited `0` after health entrypoints rather than remaining resident workers. |

Generated local artifacts from verification were removed after the run:

- `apps/web/.next`
- `apps/web/test-results`
- `apps/web/tsconfig.tsbuildinfo`
- `apps/web/playwright-report`
- `.mypy_cache`
- `.pytest_cache`
- `.ruff_cache`
- Python `__pycache__` directories created by tests/migrations

## Evidence-Backed Findings

### HIGH - Production Web Runtime Defaults To Fixture Mode

Evidence:

- `apps/web/lib/routeGuards.ts` resolves data mode as `process.env.ZULU_WEB_DATA_MODE === "api" ? "api" : "fixture"`.
- `infra/deploy/docker-compose.staging.yml` and `infra/deploy/docker-compose.production.yml` set `NEXT_PUBLIC_ZULU_API_BASE_URL` but do not set `ZULU_WEB_DATA_MODE=api`.
- `apps/web/lib/apiClient.ts` throws `API aggregation is not enabled yet; use explicit fixture mode for local UI development.` after fetching individual API resources.
- `docs/RELEASE_CANDIDATE_CHECKLIST.md` documents that API mission-control aggregation is not enabled and local UI uses explicit fixture mode.

Impact:

- A production/staging web container can start and serve fixture-backed mission-control UI unless runtime configuration explicitly overrides mode.
- Production build does not require secrets or reference folders, but production runtime is not yet proven independent of fixture-only UI data.

Required hardening:

- Add a production/staging fail-closed mode check: non-local environments must not default to fixture mode.
- Set and validate `ZULU_WEB_DATA_MODE=api` in staging/production templates once API aggregation exists.
- Add a build/runtime test proving production mode rejects fixture data unless explicitly configured for local/demo use.

### MEDIUM - Python Aggregate Verification Command Mutates Formatting

Evidence:

- Root `package.json` defines `format:py` as `uv run ruff format .`.
- Root `package.json` defines `check:py` as `npm run format:py && npm run lint:py && npm run typecheck:py && npm run test:py`.
- CI runs `npm run check:py`.

Impact:

- The CI/local aggregate check can rewrite Python source instead of failing on unformatted source.
- This weakens reproducibility because a verification command should be check-only in CI.
- This audit did not run `npm run check:py`, `npm run check`, or `npm run release:verify` to avoid production-code mutation under the prompt's change policy. Equivalent non-mutating checks were run individually where available.

Required hardening:

- Add a check-only Python format command such as `uv run ruff format --check .`.
- Update `check:py`, `check`, `release:verify`, and CI to use check-only formatting.
- Keep a separate explicit write-format command for developer use.

### MEDIUM - Web Dockerfile Uses `npm install` Instead Of `npm ci`

Evidence:

- CI uses `npm ci`.
- `apps/web/Dockerfile` uses `RUN npm install`.
- Lockfile exists and Docker build passed, but the Dockerfile install behavior is less strict than CI.

Impact:

- Docker builds are not as lockfile-strict as CI installs.
- This can allow dependency resolution differences that a clean CI `npm ci` would reject.

Required hardening:

- Replace Dockerfile web dependency install with `npm ci` after confirming the workspace lockfile is sufficient in Docker context.

### MEDIUM - Redis Queue/Cache Reset Is Not Documented As A First-Class Command

Evidence:

- Compose defines `redis-data` as a named volume.
- README documents Compose startup and health checks.
- No discovered script or documented local command explicitly resets Redis queue/cache state deterministically.

Impact:

- PostgreSQL migration reset is deterministic through `npm run migrations:validate`.
- Redis queue/cache reset appears possible through Docker volume removal but is not documented as a supported command.

Required hardening:

- Document the exact safe local reset path for Redis/queue state, likely alongside database reset instructions.
- Add a non-production guard if a reset script is introduced.

### LOW - Service Containers Are One-Shot Health Entrypoints

Evidence:

- `docker compose -f infra/docker-compose.yml ps -a` showed `signal-intelligence`, `execution`, and `learning` exited `0` after startup.
- `docs/RELEASE_CANDIDATE_CHECKLIST.md` already documents this limitation.

Impact:

- Core API/web/Postgres/Redis are runnable and healthy.
- Background services are not yet long-running workers in local Compose.

Required hardening:

- Add real worker commands or explicitly mark these services as one-shot health probes in Compose/docs.

## Files Or Modules Requiring Hardening

- `apps/web/lib/routeGuards.ts`
- `apps/web/lib/apiClient.ts`
- `infra/deploy/docker-compose.staging.yml`
- `infra/deploy/docker-compose.production.yml`
- `apps/web/Dockerfile`
- `package.json`
- `.github/workflows/ci.yml`
- `README.md`
- `docs/RELEASE_CANDIDATE_CHECKLIST.md`
- `docs/operations/deployment.md`

## Tests That Are Missing Or Weak

- No test asserts production/staging web mode cannot silently use fixture data.
- No test validates `ZULU_WEB_DATA_MODE=api` behavior because API aggregation is not enabled.
- No CI check-only Python formatting gate exists.
- No deterministic Redis queue/cache reset test or script exists.
- Docker build validation passes, but there is no test comparing Docker install strictness against `npm ci`.

## What Was Not Verified And Why

- `npm run check:py`, `npm run check`, and `npm run release:verify` were not run because they invoke `npm run format:py`, which runs `uv run ruff format .` and may rewrite production code. This prompt explicitly prohibited production-code modification.
- `npm install` was not run separately because `npm ci` is the stricter clean-install command used by CI and completed successfully. README's `npm install` remains documented for developer convenience.
- Backup and restore scripts were inspected but not executed. They require a selected backup target and restore file and can mutate database state.
- A clean machine or separate throwaway container was not provisioned. The audit used the current workspace, but `npm ci`, `uv sync --locked`, Docker build, Compose startup, and health smoke exercised the lockfiles and deployment paths.

## Recommended Matching Hardening Prompt

Harden build/install reproducibility:

- make Python CI formatting check-only;
- change web Dockerfile dependency installation to `npm ci`;
- add production/staging fixture-mode fail-closed checks and set `ZULU_WEB_DATA_MODE=api` once API aggregation exists;
- document and test deterministic Redis queue/cache reset;
- add a CI reproducibility gate that runs clean install, check-only format, lint, typecheck, tests, migration validation, Docker build, and health smoke without mutating source files.

## Final Determination

PARTIAL.

The clean install, lint, typecheck, tests, migrations, Docker build, Compose config, and API/web health smoke all passed. The area is not GO because production web mode can still default to fixture data, the Python aggregate check mutates formatting, Docker web install is less strict than CI, and Redis reset is not documented as a first-class reproducibility command.
