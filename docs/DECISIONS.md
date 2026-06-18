# Decisions

Record durable architecture, product, security, compliance, and stack decisions here.

## Decision Record Format

### YYYY-MM-DD - Title

Status: Proposed | Accepted | Superseded

Context:

- What prompted the decision.
- Constraints, risks, and alternatives considered.

Decision:

- The chosen direction.
- The exact dependency versions, protocols, schemas, services, or policies if applicable.

Verification:

- Official docs, package metadata, tests, or other sources checked.
- Commands run and results.

Consequences:

- Operational impact.
- Security, compliance, and migration considerations.
- Follow-up work.

## 2026-06-18 - Initialize Project Operating Rules

Status: Accepted

Context:

- Zulu needs durable project-level rules before implementation starts.
- No application stack or production dependency has been selected.

Decision:

- Establish root agent instructions and supporting project, verification, safety, decision, changelog, and research-boundary documents.
- Defer framework and dependency choices until a concrete implementation layer requires them.

Verification:

- Checked the repository structure before editing.
- Confirmed no package manager manifest or build system exists yet.

Consequences:

- Future prompts can rely on these project-level rules.
- The first implementation prompt must add concrete stack verification before pinning production dependencies.

## 2026-06-18 - Initialize Production Monorepo Foundation

Status: Accepted

Context:

- Zulu needs a deployable local development foundation with web, API, service packages, shared contracts, policy/risk gates, observability helpers, PostgreSQL, Redis, and reproducible dependency files.

Decision:

- Use npm workspaces for `apps/web` because npm is available and pnpm is not installed.
- Use Next.js App Router with TypeScript for the web app.
- Use uv for Python dependency locking and execution.
- Use FastAPI, Pydantic v2, and pydantic-settings for typed API boundaries and settings.
- Use PostgreSQL, Redis, Alembic, and arq as the initial persistence, cache/queue, migration, and background job stack.
- Keep Python services as importable packages in one uv-managed project until a deployment boundary requires separate published packages.

Verification:

- Checked local tool availability for Node, npm, Python, uv, Docker, and Docker Compose.
- Checked package metadata for selected npm and Python dependencies.
- Verified official docs for Next.js, FastAPI, Pydantic, Alembic, pytest, Vitest, Playwright, and arq.

Consequences:

- Developers can install, test, and run health checks locally.
- Future service extraction remains possible because services already have explicit package boundaries.
- First real persistence change must add a concrete Alembic revision and migration verification.

## 2026-06-18 - Establish Domain Contracts And Event Ledger

Status: Accepted

Context:

- Signal Station, Automation Station, learning, risk, and compliance need shared domain objects that later prompts cannot silently reinterpret.
- Accepted signals, broker requests, execution lifecycle events, and audit events require durable database constraints.

Decision:

- Add strict Pydantic v2 contracts in `packages/contracts` and mirrored TypeScript types in `apps/web/lib/contracts.ts`.
- Use SQLAlchemy models in the API data layer as the database mapping source.
- Create the initial Alembic migration for tenants, users, subscriptions, broker connections, market data, options, headlines, market weather, feature vectors, strategy candidates, clean signals, policy/risk decisions, execution intents, broker order requests, lifecycle events, positions, outcome labels, model records, user overrides, incidents, audit events, and outbox events.
- Use PostgreSQL constraints, tenant indexes, idempotency uniqueness, JSONB context payloads, decimal columns, and triggers for immutable audit/order events and audited clean-signal state transitions.

Verification:

- Added contract serialization, schema, and invariant tests.
- Added API metadata registration test.
- Added migration validation script for clean PostgreSQL upgrade/downgrade verification.

Consequences:

- Later services must use these contracts rather than inventing incompatible trading objects.
- Clean-signal state transitions require an audit event before database update.
- Future contract changes must be recorded as compatibility decisions.

## 2026-06-18 - Establish Market Data And Context Ingestion Boundary

Status: Accepted

Context:

- Signal Station and Automation Station need validated market context before scoring, policy, risk, or execution logic can use provider data.
- Provider capabilities vary, especially for options greeks, implied volatility, open interest, news, and calendar data.

Decision:

- Create typed provider adapter protocols for stocks, options, headlines, calendars, and broad market context.
- Use a deterministic fixture provider for tests and local development.
- Keep live provider clients environment-gated and disabled unless explicitly configured.
- Normalize provider payloads into strict contracts with provenance, freshness, spread, liquidity, and missing-data checks.
- Generate `CanonicalFeatureVectorV1` with stable `canonical_v1.*` names and explicit availability flags for optional options data.
- Classify market weather with transparent components and a compact shared snapshot.

Verification:

- Added provider, normalization, feature, weather, stale-data, missing-data, circuit-breaker, and fixture integration tests.
- Verification commands are recorded in the final task report for this change.

Consequences:

- Future provider adapters must satisfy the same interfaces and quality gates.
- Missing greeks, volume, open interest, or news cannot silently become neutral values.
- Feature schema changes require a new schema version or a documented compatibility decision.
