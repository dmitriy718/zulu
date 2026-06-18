# Verification 03: Contracts, Database, Migrations, and Audit Ledger

Date: 2026-06-18

Result: NO-GO

Zulu has strong foundational contracts, a broad first migration, immutable audit/order lifecycle triggers, and passing test suites. This verification area is still NO-GO because several safety-critical guarantees are not yet enforced at the durable source-of-truth layer, and the execution path does not persist its audit events into the immutable database ledger.

## Scope Inspected

- Project instructions: `AGENTS.md`
- Relevant docs:
  - `docs/architecture/contracts.md`
  - `docs/architecture/event_ledger.md`
  - `docs/architecture/signal_intelligence.md`
  - `docs/architecture/policy_and_risk.md`
  - `docs/architecture/execution_and_reconciliation.md`
  - `docs/SAFETY_AND_COMPLIANCE.md`
  - `docs/VERIFY_EVERY_TASK.md`
  - `docs/RELEASE_CANDIDATE_CHECKLIST.md`
  - `docs/research/current_stack_verification.md`
  - `docs/research/nova_reference_lessons.md`
- Contract source: `packages/contracts/src/zulu_contracts/`
- Contract tests: `packages/contracts/tests/`
- Mirrored web types: `apps/web/lib/contracts.ts`
- Web contract tests: `apps/web/tests/contracts.test.ts`
- API schemas and platform models: `services/api/src/zulu_api/`
- Database models: `services/api/src/zulu_api/data/models.py`
- Migration and validator:
  - `infra/migrations/versions/424eff242b2b_create_domain_ledger_schema.py`
  - `infra/scripts/validate_migrations.py`
- Execution authority, broker gate, and reconciliation code:
  - `services/execution/src/zulu_execution/`
  - `services/execution/tests/test_adapter_safety.py`
- Integration and release anti-regression tests:
  - `tests/integration/test_execution_gate_integration.py`
  - `scripts/final_anti_regression.py`

Nova/reference repositories were not inspected.

## Command Map Used

Discovered from `package.json`, `apps/web/package.json`, `pyproject.toml`, and repo docs:

| Area | Command |
| --- | --- |
| Python lint | `npm run lint:py` |
| Python typecheck | `npm run typecheck:py` |
| Python tests | `npm run test:py` |
| Targeted contract/API/execution tests | `uv run pytest packages/contracts/tests services/api/tests/test_data_models.py services/execution/tests/test_adapter_safety.py tests/integration/test_execution_gate_integration.py` |
| Signal pipeline invariant tests | `uv run pytest services/signal-intelligence/tests/test_signal_pipeline.py` |
| Migration validation | `npm run migrations:validate` |
| Final anti-regression checks | `npm run release:anti-regression` |
| Web typecheck | `npm --workspace apps/web run typecheck` |
| Web tests | `npm --workspace apps/web run test` |

Not run:

- `npm run check`, `npm run check:py`, and `npm run release:verify` because `check:py` invokes `npm run format:py`, which runs `ruff format .` and may mutate production code. This prompt allowed reports and temporary artifacts only.
- Docker build/compose checks because this verification area was limited to contracts, database, migrations, event/outbox, and audit ledger. Compose reproducibility was covered by verification 02.

## Commands Run And Results

| Command | Result | Evidence |
| --- | --- | --- |
| `npm run lint:py` | PASS | `ruff check .` returned `All checks passed!` |
| `npm run typecheck:py` | PASS | `mypy services packages tests` returned `Success: no issues found in 75 source files` |
| `uv run pytest packages/contracts/tests services/api/tests/test_data_models.py services/execution/tests/test_adapter_safety.py tests/integration/test_execution_gate_integration.py` | PASS | `26 passed in 0.51s` |
| `npm --workspace apps/web run typecheck` | PASS | `tsc --noEmit` exited 0 |
| `npm --workspace apps/web run test -- --run apps/web/tests/contracts.test.ts` | FAIL, command-path issue | Vitest runs from `apps/web`; repo-root test path did not match include pattern |
| `npm --workspace apps/web run test -- --run tests/contracts.test.ts` | PASS | `1 passed`, `2 tests passed` |
| `npm run migrations:validate` | PASS | Alembic downgraded to base, upgraded to head, validated expected tables/triggers, and downgraded to base |
| `npm run release:anti-regression` | PASS | Passed checks for no silent accepted-signal disappearance, broker gate prerequisites, live default disabled, unsupported assets, options metadata, stop loss, idempotency, tenant isolation, redaction, promotion gates, kill switches, stale provider data, reconciliation incidents, and metrics declarations |
| `npm run test:py` | PASS | `93 passed, 2 warnings in 1.22s` |
| `uv run pytest services/signal-intelligence/tests/test_signal_pipeline.py` | PASS | `10 passed in 0.10s` |
| `npm --workspace apps/web run test` | PASS | `3 passed`, `9 tests passed` |

Transient verification artifacts `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, and `apps/web/tsconfig.tsbuildinfo` were removed after the run.

## Evidence-Backed Findings

### CRITICAL: Execution audit events are not durably persisted to the immutable audit ledger

Evidence:

- `services/execution/src/zulu_execution/lifecycle.py:48-57` defines `ExecutionRecord.audit_events` as an in-memory list.
- `services/execution/src/zulu_execution/lifecycle.py:113-123`, `137-147`, `190-199`, and `217-227` append policy, risk, broker request, and broker response audit events to that in-memory record.
- `services/execution/src/zulu_execution/lifecycle.py:201` calls `broker_adapter.submit_order(...)`.
- The execution service search found no SQLAlchemy session/repository path writing those execution audit events to `services/api/src/zulu_api/data/models.py:522-539` (`audit_events`).
- `services/execution/tests/test_adapter_safety.py:141` verifies `len(result.record.audit_events) >= 4`, but does not verify persistence to the immutable audit table.

Impact:

The broker path is auditable in memory during process lifetime, but not proven durable in the append-only ledger. If the process crashes after a paper/live broker call, the required audit evidence can be lost.

Required hardening:

- Add a persistent execution repository/unit-of-work that writes `PolicyDecision`, `RiskDecision`, `ExecutionIntent`, `BrokerOrderRequest`, `OrderLifecycleEvent`, `AuditEvent`, incidents, and outbox events transactionally where appropriate.
- Add integration tests proving a broker call cannot complete unless its audit events are committed to `audit_events`.
- Add crash/retry tests for idempotent recovery.

### HIGH: Exported legacy signal contracts are not strict and can drift from `CleanSignalV1`

Evidence:

- `packages/contracts/src/zulu_contracts/domain.py:12-18` defines `StrictContract` with `extra="forbid"`, `strict=True`, and `validate_assignment=True`.
- `packages/contracts/src/zulu_contracts/signals.py:19-25` defines `SignalCandidate(BaseModel)`, not `StrictContract`.
- `packages/contracts/src/zulu_contracts/signals.py:28-44` defines `SignalDisposition(BaseModel)`, not `StrictContract`.
- `SignalCandidate` uses `confidence_score: float` instead of the decimal-safe score type used by `CleanSignalV1` at `packages/contracts/src/zulu_contracts/domain.py:336-340`.

Impact:

The prompt required strict contracts for raw signal and decision objects. These exported public contracts are weaker than the canonical domain contracts and can accept/ignore loose data in ways the stricter contract layer would reject.

Required hardening:

- Either remove/deprecate the legacy signal module from public exports or convert these models to strict Zulu domain contracts.
- Align naming and fields with canonical signal lifecycle terminology.
- Add tests proving extra fields, naive timestamps, invalid scores, and unsafe execution dispositions are rejected.

### HIGH: Tenant, subscription, and user-role contracts are not centralized in `packages/contracts`

Evidence:

- Database tables exist in `services/api/src/zulu_api/data/models.py:33-63`.
- API/platform models exist in `services/api/src/zulu_api/auth.py` and `services/api/src/zulu_api/platform.py`.
- Web mirrors include plan/subscription types in `apps/web/lib/contracts.ts:317-329`.
- `packages/contracts/src/zulu_contracts/domain.py` does not define shared strict `Tenant`, `Subscription`, or `UserRole` contracts.

Impact:

Tenant isolation and subscription gating are safety-critical, but their shared source of truth is split across API-only models and hand-written TypeScript. This creates drift risk for authorization and feature gating.

Required hardening:

- Add strict shared contracts for tenant, user, user role, subscription, product mode, automation environment, and plan status.
- Use those contracts in API responses and mirrored/generated web types.
- Add tenant/role/subscription serialization tests.

### HIGH: Frontend contract types are hand-mirrored and have no schema drift check

Evidence:

- `docs/DECISIONS.md:96` states strict Pydantic contracts are mirrored in `apps/web/lib/contracts.ts`.
- `docs/research/current_stack_verification.md:91` says generated TypeScript clients are deferred.
- `apps/web/lib/contracts.ts:1-329` contains hand-written interfaces.
- `apps/web/tests/contracts.test.ts:22-35` checks only a small static key list for `CleanSignalV1`; it does not compare backend schemas to frontend types.

Impact:

Backend/frontend contract drift is not automatically detectable. A Python contract change can pass backend tests while the web app consumes stale or incomplete types.

Required hardening:

- Generate JSON Schema/OpenAPI artifacts from the canonical Python contracts.
- Generate TypeScript types from those artifacts.
- Add a CI drift check that fails when generated types differ from committed types.

### HIGH: Core `clean_signals` database constraints are incomplete for score ranges and finite enums

Evidence:

- `services/api/src/zulu_api/data/models.py:247-249` stores `confidence_score`, `risk_score`, and `quality_score` as non-null numeric values.
- `services/api/src/zulu_api/data/models.py:267-305` includes checks for asset type, option metadata, stop loss, entry zone, entry trigger, take-profit presence, invalidations, decision trace, expiry, feature hash, acceptance status, and terminal state.
- There are no DB check constraints in that block enforcing `confidence_score`, `risk_score`, or `quality_score` between 0 and 1.
- `direction`, `timeframe`, and `policy_status` are non-null strings at `services/api/src/zulu_api/data/models.py:240-260`, but no table-level checks constrain them to canonical enum values.

Impact:

The Pydantic layer rejects invalid scores/enums, but direct ingestion, migration scripts, admin tools, or future services can write invalid safety-critical signal state to the database.

Required hardening:

- Add DB check constraints for score ranges.
- Add DB check constraints for `direction`, `timeframe`, `policy_status`, and ticker format where practical.
- Add migration validation tests that insert invalid rows and assert database rejection.

### HIGH: Outbox idempotency is optional at the database layer

Evidence:

- `services/api/src/zulu_api/data/models.py:550` defines `idempotency_key` as nullable.
- `services/api/src/zulu_api/data/models.py:556` adds a unique constraint on `(tenant_id, idempotency_key)`.
- PostgreSQL unique constraints allow multiple `NULL` values, so duplicate non-idempotent events are possible.
- The migration matches this nullable design at `infra/migrations/versions/424eff242b2b_create_domain_ledger_schema.py:237` and `246`.

Impact:

The outbox can store multiple events for the same tenant without idempotency keys. This weakens recoverability and duplicate-processing protection for cross-service events.

Required hardening:

- Make `outbox_events.idempotency_key` non-null.
- Add event status, attempts, last error, locked/claimed metadata, and replay-safe processing fields.
- Add tests proving duplicate outbox events are rejected and failed events are recoverable.

### HIGH: Migration validation proves shape, not safety behavior

Evidence:

- `infra/scripts/validate_migrations.py:8-34` verifies expected table names.
- `infra/scripts/validate_migrations.py:52-59` verifies only `audit_events_immutable` and `clean_signal_guard` trigger counts.
- The migration creates `order_lifecycle_events_immutable` at `infra/migrations/versions/424eff242b2b_create_domain_ledger_schema.py:757-761`, but the validator does not check it.
- The validator does not exercise invalid inserts for missing stop loss, invalid scores, missing option metadata, stale market data, duplicate outbox idempotency, audit immutability, order lifecycle immutability, or clean signal transition audit requirements.

Impact:

`npm run migrations:validate` confirms that the migration can bootstrap and downgrade the schema, but it does not prove the database enforces the most important safety invariants.

Required hardening:

- Add migration behavior tests against PostgreSQL.
- Check every expected trigger, including `order_lifecycle_events_immutable`.
- Add negative insert/update/delete tests for core safety invariants.

### MEDIUM: `clean_signals` terminal-state consistency is only partially enforced

Evidence:

- `services/api/src/zulu_api/data/models.py:294-302` constrains accepted-signal terminal state values.
- There is no DB constraint tying `acceptance_status = 'terminal'` to `terminal_state is not null`, or requiring `terminal_state is null` for non-terminal rows.
- `infra/migrations/versions/424eff242b2b_create_domain_ledger_schema.py:782-799` requires an audit event for state or terminal-state updates.

Impact:

The database prevents deletes and audits state transitions, but it still permits inconsistent persisted combinations such as `acceptance_status = 'terminal'` with `terminal_state is null`.

Required hardening:

- Add a check constraint for valid `acceptance_status` and `terminal_state` combinations.
- Add an aging/monitoring job for accepted signals that have not reached a terminal path within policy-defined time.

## Positive Evidence

- `CleanSignalV1` includes required safety fields and strict validation:
  - Asset type/ticker/option metadata: `packages/contracts/src/zulu_contracts/domain.py:323-329`
  - Entry zone, entry trigger, stop loss, take-profit levels: `packages/contracts/src/zulu_contracts/domain.py:331-335`
  - Confidence/risk/quality scores: `packages/contracts/src/zulu_contracts/domain.py:336-340`
  - Market weather, market data, context, theses, invalidation, model metadata, feature hash, policy status, expiry, and decision trace: `packages/contracts/src/zulu_contracts/domain.py:341-357`
  - Options metadata, stale market data, expiry, schema, and feature hash invariants: `packages/contracts/src/zulu_contracts/domain.py:364-378`
- `BrokerOrderRequest` requires `idempotency_key`: `packages/contracts/src/zulu_contracts/domain.py:427-438`.
- `OrderLifecycleEvent` requires reconciliation or incident: `packages/contracts/src/zulu_contracts/domain.py:446-468`.
- The migration creates immutable audit and order lifecycle triggers: `infra/migrations/versions/424eff242b2b_create_domain_ledger_schema.py:740-761`.
- The migration creates a clean signal guard that blocks deletion, rejects stale market data, and requires `zulu.audit_event_id` for signal state transitions: `infra/migrations/versions/424eff242b2b_create_domain_ledger_schema.py:765-810`.
- `release:anti-regression` passed all declared final safety probes.

## Files Or Modules Requiring Hardening

- `services/execution/src/zulu_execution/lifecycle.py`
- `services/execution/tests/test_adapter_safety.py`
- `tests/integration/test_execution_gate_integration.py`
- `packages/contracts/src/zulu_contracts/signals.py`
- `packages/contracts/src/zulu_contracts/domain.py`
- `apps/web/lib/contracts.ts`
- `apps/web/tests/contracts.test.ts`
- `services/api/src/zulu_api/data/models.py`
- `infra/migrations/versions/424eff242b2b_create_domain_ledger_schema.py`
- `infra/scripts/validate_migrations.py`
- Add new migration behavior tests under `services/api/tests/` or `tests/integration/`

## Tests Missing Or Weak

- No test proves execution audit events are persisted to the immutable `audit_events` table before/with broker calls.
- No DB-level negative tests for invalid signal scores, invalid direction/timeframe/policy status, missing terminal state on terminal rows, or duplicate nullable outbox events.
- No generated TypeScript drift test against canonical Python schemas.
- Web contract tests assert only compile-time shape snippets, not schema parity or runtime validation.
- Migration validation does not test safety behavior; it only validates table presence, two trigger counts, and downgrade.
- Shared tenant/subscription/user-role contract tests are missing because those contracts are not centralized in `packages/contracts`.

## What Was Not Verified And Why

- Full `npm run check`, `npm run check:py`, and `npm run release:verify` were not run because they include `ruff format .`, which may mutate production code and violates this prompt's change policy.
- Docker build/compose runtime was not rerun because this verification focused on contracts, database, migrations, outbox, and audit ledger. See verification 02 for build/install/command reproducibility.
- Actual live broker execution was not verified and must remain disabled by default.
- Database behavior tests beyond `migrations:validate` were not available in the repo.

## Recommended Matching Hardening Prompt

```text
Read AGENTS.md, docs/architecture/contracts.md, docs/architecture/event_ledger.md, docs/architecture/execution_and_reconciliation.md, and docs/verification/03_contracts_database_migrations_and_audit_ledger.md first.

Objective:
Harden Zulu's contract/database/audit layer so verification 03 can move from NO-GO to GO.

Requirements:
1. Persist execution-path PolicyDecision, RiskDecision, ExecutionIntent, BrokerOrderRequest, OrderLifecycleEvent, AuditEvent, SystemIncident, and outbox events through a durable repository before/with any broker adapter call.
2. Prove no broker adapter call can complete unless required audit events are committed to the immutable audit ledger.
3. Convert or remove legacy exported signal contracts that are not strict.
4. Add shared strict contracts for tenant, user, user role, subscription, product mode, automation environment, and plan status.
5. Add generated TypeScript contract output from canonical Python schemas or an equivalent drift-proof schema generation workflow.
6. Add database constraints for clean signal score ranges, direction, timeframe, policy status, ticker format where practical, terminal-state consistency, and non-null outbox idempotency.
7. Extend migration validation with PostgreSQL negative tests for core safety invariants, immutable audit/order lifecycle tables, clean signal transition audit requirements, and outbox duplicate prevention.
8. Update docs/architecture/contracts.md, docs/architecture/event_ledger.md, docs/DECISIONS.md, docs/CHANGELOG.md, and this verification report's follow-up status.

Verification:
Run the discovered lint, typecheck, contract tests, migration behavior tests, integration tests, web type generation/drift check, and final anti-regression script. Do not fabricate results.
```

## Final Determination

NO-GO for verification area 03.

Reason: safety-critical contract tests pass, and the migration can bootstrap/downgrade PostgreSQL, but durable execution audit persistence, strict shared platform contracts, generated type drift protection, DB-level safety constraints, and outbox idempotency are not yet strong enough to trust this layer as Zulu's source of truth for safety-critical flows.
