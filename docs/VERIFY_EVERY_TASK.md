# Verify Every Task

Run the checks relevant to the layer changed. If a stack or command has not been created yet, report it as not available and add the required command when that layer is introduced.

## Frontend Changes

Required once a frontend package exists:

- Format: `npm run format:web`
- Lint: `npm run lint:web`
- Typecheck: `npm run typecheck:web`
- Unit tests: `npm run test:web`
- Build: `npm run build:web`
- Visual or browser verification for user-facing flows.

## Backend Changes

Required once a backend package exists:

- Format: `npm run format:py`
- Lint: `npm run lint:py`
- Typecheck: `npm run typecheck:py`
- Unit and integration tests: `npm run test:py`
- Integration tests for persistence, auth, broker adapter boundaries, queues, and external-service adapters touched by the change.

## Contract Changes

Required when API, event, schema, or generated-client contracts change:

- Validate schemas.
- Regenerate typed clients or server stubs.
- Run contract tests for producers and consumers.
- Run backward-compatibility checks or document the breaking change in `docs/DECISIONS.md`.

## Migration Changes

Required when database migrations are added or changed:

- Apply migrations to a clean local database.
- Apply migrations to an existing local database with representative previous state.
- Run rollback or forward-fix verification according to the selected migration strategy.
- Run repository tests that touch changed tables or persistence behavior.

## Execution And Risk Logic Changes

Required when signal acceptance, PolicyGate, RiskGate, idempotency, audit, broker adapters, or execution state changes:

- Unit tests for allowed, rejected, and failure paths.
- Integration tests proving no broker adapter call can occur without PolicyGate, RiskGate, idempotency key, and audit event.
- Tests proving every accepted signal reaches durable execution-attempt or terminal rejection state.
- Tests for live-trading disabled-by-default behavior.
- Tests for duplicate request/idempotency behavior.

## When Commands Fail

Do not hide or rename failing checks. Inspect the failure, fix the smallest relevant cause, and rerun the failed command plus any dependent checks. If a command cannot run because infrastructure is missing, report that limitation directly in the final task report.
