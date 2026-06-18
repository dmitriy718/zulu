# Nova Reference Lessons

Use this file only if the Nova repository is inspected as read-only reference material.

## Reference Use Rules

- Record lessons, risks, requirements, and failure modes only.
- Do not paste source code, tests, schemas, package names, service names, UI copy, environment variable names, or runtime behavior from Nova.
- Explain how Zulu will implement any useful lesson independently.
- Keep these notes internal to `docs/research/`.

## Lesson Template

### YYYY-MM-DD - Topic

Reference Area:

- Docs, architecture notes, tests, or code path inspected.

Lesson:

- What was learned.

Failure Mode Or Risk:

- What Zulu should avoid or explicitly handle.

Zulu Reimplementation Plan:

- How Zulu will address the lesson independently.

Boundaries Checked:

- Confirm no copied source, preserved API, schema, package name, service name, environment variable, UI copy, or test was introduced.

## Inspection Log

### 2026-06-18 - Monorepo Foundation

Reference Area:

- None.

Lesson:

- No Nova inspection was performed for this initialization task.

Failure Mode Or Risk:

- Avoided introducing reference-derived assumptions before Zulu has its own contracts.

Zulu Reimplementation Plan:

- Build the initial monorepo solely from Zulu project requirements and verified stack metadata.

Boundaries Checked:

- Confirm no copied source, preserved API, schema, package name, service name, environment variable, UI copy, or test was introduced.
