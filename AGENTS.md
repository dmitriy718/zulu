# Repository Guidelines

Zulu is a greenfield, standalone product. Treat this repository and these instructions as the source of truth for all future work.

## Product Scope

Zulu is a stocks/options-only trading intelligence and automation platform.

- Signal Station: users receive deeply filtered, contextualized trade signals.
- Automation Station: approved signals may flow into a strictly risk-governed execution engine.

Do not add crypto, forex, futures, gambling/casino framing, or language that promises profit, flawless performance, or market-beating results.

## Greenfield Boundary

Nova may be inspected as read-only reference material only. Do not import, copy, migrate, preserve, shim, or depend on anything from Nova or any previous project, including code, docs, tests, changelog entries, APIs, schemas, package names, service names, UI copy, environment variable namespaces, infrastructure, or runtime behavior.

If Nova is inspected, first record reference-only lessons in `docs/research/nova_reference_lessons.md` and explain how Zulu will reimplement any useful lesson independently. Keep Nova out of runtime code, public product docs, package metadata, service names, database tables, environment variables, and UI copy.

## Engineering Standard

Production-ready beats prototype. Correctness beats speed. Risk controls beat automation. Auditability beats hidden magic. Explicit failures beat silent failures. Verified work beats claimed work. Deterministic contracts beat loose JSON. Bounded autonomy beats unsafe self-modification.

Before editing, inspect the current folder and read this file. Build the smallest safe complete slice for the prompt. Do not create fake passing results or hide failing tests.


## Saving Locations

Whenever working on anything inside of zulu, please save your logs and reports to the appropriate location:

- `docs/verification/` for verification reports.
- `docs/hardening/` for hardening reports and issue closure notes.
- `docs/release/` for release-candidate evidence.
- `docs/incidents/` for security, trading-safety, or data-integrity incident notes.

If possible please try following default naming convention : MMDDYYYY_##_TITLE.md unless otherwise specified.


## Safety Rules

live trading disabled by default: live trading must remain impossible unless explicit environment, tenant, user, and policy gates are all satisfied.

No accepted signal may silently disappear. Every accepted trade signal must become either a durable execution attempt or a durable terminal rejection with a reason.

No broker adapter call may occur without all of the following:

- PolicyGate approval.
- RiskGate approval.
- Idempotency key.
- Audit event written for the attempted action.

Do not use fake market data, fake broker fills, fake model metrics, or fake verification as evidence of production readiness. Clearly label fixtures, mocks, simulations, and test doubles.

Do not log secrets, broker credentials, user PII, account IDs, raw tokens, private hostnames, private IPs, or full stack traces containing sensitive values.

## Verification Workflow

For every meaningful change, add or update tests for the behavior changed. Run formatting, linting, typechecking, unit tests, and integration tests relevant to the changed layer. Follow `docs/VERIFY_EVERY_TASK.md` for layer-specific checks.

Current root commands:

- Web checks: `npm run check:web`
- Python checks: `npm run check:py`
- Docker Compose config: `npm run compose:config`
- Full available check set: `npm run check`

If a command fails, inspect the failure, repair the smallest cause, and rerun the relevant command. If a command is not available because the stack has not been created yet, report it as not available and do not imply it passed.

## Final Report Format

End each task with:

- Files changed.
- Behavior implemented.
- Tests added or updated.
- Commands run with pass, fail, or not-available results.
- Known limitations.
- Next-prompt readiness.
