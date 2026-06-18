# Reference Boundaries

Nova may be inspected only as read-only reference material. Zulu must remain a greenfield, standalone product.

## Allowed

- Read Nova docs, changelogs, review notes, tests, architecture notes, and selected code paths to identify lessons and failure modes.
- Summarize lessons in `docs/research/nova_reference_lessons.md`.
- Convert independently justified lessons into new Zulu requirements.
- Use lessons to design new Zulu architecture, contracts, tests, and safety checks.

## Not Allowed

- Copy source code, tests, docs, schemas, configs, fixtures, seeds, UI copy, package names, service names, environment variable namespaces, database table names, infrastructure definitions, or changelog entries.
- Preserve Nova APIs, data models, module boundaries, runtime behavior, compatibility shims, or migration paths.
- Make Zulu require Nova to run, test, deploy, or understand the product.
- Describe Zulu as a migration, rewrite, fork, continuation, or derivative.
- Put Nova names in runtime code, public product docs, package metadata, service names, database tables, environment variables, or UI copy.

## Required Process

Before implementing anything based on reference inspection:

1. Add a dated entry to `docs/research/nova_reference_lessons.md`.
2. State the lesson and the failure mode.
3. State the independent Zulu implementation plan.
4. Confirm the boundary checks.

If a boundary is ambiguous, stop and choose a new Zulu-native design.
