# Current Stack Verification

Use this file before pinning production dependencies. Prefer official documentation and package manager metadata over blogs or examples.

## Verification Template

### YYYY-MM-DD - Dependency Or Stack Choice

Purpose:

- What capability this dependency or stack provides.

Candidates Considered:

- Name, official source, current version, and why it was considered.

Selected Version:

- Exact package name and version.

Sources Checked:

- Official docs URL or local package metadata command.

Decision:

- Why this choice fits Zulu.

Verification Commands:

- Commands run and pass/fail result for each command.

Operational Notes:

- Security, licensing, deployment, upgrade, or maintenance considerations.

## 2026-06-18 - Monorepo Foundation Stack

Purpose:

- Initialize a deployable local development foundation for the web app, API, service packages, contracts, policy/risk packages, observability, persistence, queue/cache, and tests.

Selected Versions:

- Node.js `24.14.1`, npm `11.11.0`
- Python `3.12.3`, uv `0.10.12`
- Docker `29.5.3`, Docker Compose `5.1.4`
- Next.js `16.2.9`, React `19.2.7`, React DOM `19.2.7`
- TypeScript `6.0.3`, ESLint `9.39.1`, eslint-config-next `16.2.9`, Prettier `3.8.4`
- Vitest `4.1.9`, Playwright `1.61.0`, jsdom `29.1.1`
- FastAPI `0.137.2`, Pydantic `2.13.4`, pydantic-settings `2.14.1`, Uvicorn `0.49.0`
- PostgreSQL image `postgres:18.1`, Redis image `redis:8.4`
- SQLAlchemy `2.0.51`, Alembic `1.18.4`, psycopg `3.3.4`
- redis-py `5.3.1`, arq `0.28.0`
- pytest `9.1.0`, Ruff `0.15.17`, mypy `2.1.0`, HTTPX `0.28.1`, structlog `26.1.0`
- setuptools `82.0.1` for local package builds

Sources Checked:

- Next.js App Router installation docs: https://nextjs.org/docs/app/getting-started/installation
- Next.js TypeScript docs: https://nextjs.org/docs/app/api-reference/config/typescript
- FastAPI docs: https://fastapi.tiangolo.com/
- FastAPI Pydantic v2 migration note: https://fastapi.tiangolo.com/how-to/migrate-from-pydantic-v1-to-pydantic-v2/
- Pydantic v2 docs: https://docs.pydantic.dev/
- Alembic docs: https://alembic.sqlalchemy.org/
- Alembic tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- pytest docs: https://docs.pytest.org/en/stable/getting-started.html
- Vitest guide: https://vitest.dev/guide/
- Playwright docs: https://playwright.dev/docs/intro
- arq docs: https://arq-docs.helpmanual.io/

Package Metadata Checked:

- `npm view next version engines peerDependencies --json` confirmed Next.js `16.2.9` supports Node `>=20.9.0` and React `^19.0.0`.
- `npm view react version --json` and `npm view react-dom version --json` returned `19.2.7`.
- `npm view vitest version engines --json` returned `4.1.9` and Node support including `>=24.0.0`.
- `npm view @playwright/test version engines --json` returned `1.61.0` and Node `>=18`.
- `npm view eslint-config-next@16.2.9 peerDependencies --json` confirmed ESLint `>=9.0.0`.
- `npm view eslint@9.39.1 version engines --json` confirmed Node support including `>=21.1.0`.
- `python3 -m pip index versions ...` checked latest Python package versions because `uv pip index` is unavailable in uv `0.10.12`.
- `python3 -m pip index versions setuptools` returned `82.0.1`.
- `uv sync` rejected redis-py `8.0.0` because arq `0.28.0` requires `redis>=4.2.0,<6`; redis-py `5.3.1` was selected as the newest compatible release from the checked metadata.
- `docker manifest inspect postgres:18.1` and `docker manifest inspect redis:8.4` passed.

Decision:

- Use npm workspaces because npm is installed and pnpm is not.
- Use uv for Python dependency locking because uv is installed and provides reproducible `uv.lock`.
- Use Next.js App Router for the web app because current official docs cover App Router, TypeScript, ESLint, and route handlers.
- Use FastAPI with Pydantic v2 for typed HTTP/API contracts.
- Use Pydantic models as the initial contract source of truth; generated TypeScript clients are deferred until API schemas stabilize.
- Use arq as the maintained Redis-backed Python job system because it supports async workers and Redis job uniqueness semantics.
- Use PostgreSQL and Redis through Docker Compose for local deployability.

Verification Commands:

- `node --version && npm --version && corepack --version && pnpm --version || true` passed; pnpm was not installed.
- `python3 --version && uv --version && poetry --version || true && pip --version` passed; Poetry was not installed.
- `docker --version && docker compose version` passed.

Operational Notes:

- No live broker credentials or live trading enablement variables are present.
- `.env.example` contains local-only safe placeholders.
- Future API contract generation should be added when endpoint schemas stabilize enough for generated clients.
- `npm audit --audit-level=high` passes, but `npm audit` reports a moderate PostCSS advisory through current stable Next.js `16.2.9`; npm's suggested fix is a breaking downgrade to Next `9.3.3`, so this is documented as a known dependency watch item rather than applied.

## 2026-06-18 - Web Interface Upgrade Packages

Purpose:

- Upgrade the web interface presentation with current production UI packages for iconography, class composition, and future motion primitives.

Selected Versions:

- `tailwindcss` `4.3.1`
- `@tailwindcss/postcss` `4.3.1`
- `lucide-react` `1.21.0`
- `clsx` `2.1.1`
- `motion` `12.40.0`

Sources Checked:

- npm package metadata was checked from the local environment with network access.

Package Metadata Checked:

- `npm view tailwindcss version` returned `4.3.1`.
- `npm view @tailwindcss/postcss version` returned `4.3.1`.
- `npm view lucide-react version` returned `1.21.0`.
- `npm view clsx version` returned `2.1.1`.
- `npm view motion version` returned `12.40.0`.
- `npm install --workspace apps/web tailwindcss@4.3.1 @tailwindcss/postcss@4.3.1` completed and updated the reproducible npm lockfile.
- `npm install --workspace apps/web lucide-react@1.21.0 clsx@2.1.1 motion@12.40.0` completed and updated the reproducible npm lockfile.

Decision:

- Use Tailwind CSS v4 through the current PostCSS plugin as the CSS processing layer while preserving Zulu's custom product-specific visual system in `app/styles.css`.
- Use `lucide-react` for professional icon-led controls and status surfaces.
- Use `clsx` for explicit status class composition.
- Add `motion` as the current maintained motion package for future client-side micro-interactions while keeping critical safety/status rendering server-friendly.

Verification Commands:

- `npm --workspace apps/web run lint` passed.
- `npm --workspace apps/web run typecheck` passed.
- `npm --workspace apps/web run test` passed.
- `npm --workspace apps/web run build` passed.

Operational Notes:

- `npm audit` still reports the previously documented moderate PostCSS advisory through Next.js; high-level audit policy remains unchanged.
