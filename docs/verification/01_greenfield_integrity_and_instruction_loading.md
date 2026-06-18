# Greenfield Integrity And Instruction Loading Verification

Date: 2026-06-18

Result: GO

## Scope Inspected

- Root instructions: `AGENTS.md`.
- Project docs: `README.md`, `docs/PROJECT_PRINCIPLES.md`, `docs/SAFETY_AND_COMPLIANCE.md`, `docs/VERIFY_EVERY_TASK.md`, `docs/DECISIONS.md`, `docs/CHANGELOG.md`, `docs/RELEASE_CANDIDATE_CHECKLIST.md`, architecture docs, operations docs, design docs, runbooks, and research docs.
- Package and command surfaces: `package.json`, `apps/web/package.json`, `pyproject.toml`, `package-lock.json`, `uv.lock`, `.github/workflows/ci.yml`.
- Runtime and deployment surfaces: `infra/docker-compose.yml`, `infra/deploy/docker-compose.staging.yml`, `infra/deploy/docker-compose.production.yml`, `apps/web/Dockerfile`, `infra/Dockerfile.python`, `.env.example`, `infra/env/*.env.example`.
- Discovery and isolation settings: `.gitignore`, `.dockerignore`, npm workspaces, setuptools package discovery, pytest discovery, mypy discovery, Docker build contexts, Compose service names.
- Runtime/public surfaces: `apps/web/app`, `apps/web/components`, `apps/web/lib`, `apps/web/public`, `services`, `packages`, `infra/migrations`, `scripts`, and `tests`.
- Reference setup: no in-repo `.reference/` or `reference/` directory was present. A sibling reference repository exists at `/home/user/Desktop/NovaByHorizon`, outside the Zulu repository.

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

Discovered from `pyproject.toml`:

- Python package discovery is restricted to `include = ["zulu_*"]`.
- Package roots are the Zulu package and service `src` directories only.
- Pytest discovery is restricted to Zulu package/service tests and `tests`.
- Mypy discovery is restricted to `packages`, `services`, and `tests`.

Discovered from CI:

- CI installs with `npm ci` and `uv sync --locked`.
- CI runs web checks, Python checks, migration validation, Compose config validation, Docker build validation, dependency audit, secret scan, and anti-regression gate.

## Commands Run And Results

| Command | Result | Evidence |
| --- | --- | --- |
| `sed -n '1,260p' AGENTS.md` | PASS | Confirmed instructions loaded and inspected. |
| `find . -name AGENTS.md ...` | PASS | Found only root `AGENTS.md`; no nested agent instructions were present. |
| `sed` reads for README, safety, principles, verify docs, reference docs, manifests, CI, Docker, env, ignore files | PASS | Confirmed command surfaces and greenfield/reference instructions. |
| `python3` AGENTS content check | PASS | `greenfield`, `standalone`, `stocks/options-only`, `live trading disabled by default`, and `no accepted signal may silently disappear` all returned `True`. |
| Exact prior-project scan excluding dependencies, `.git`, `.venv`, and `docs/research`: `rg ... '\bNova\b|\bnova\b|NovaByHorizon|\bHorizon\b|NOVA_|HORIZON_|nova_|horizon_|/NovaByHorizon|\.reference/|reference/' ...` | PASS | Only `.gitignore`, `.dockerignore`, and the Next.js documentation URL containing `reference/` matched. No runtime/public Nova or prior-project name was found. |
| Broader scan including `docs/research` | PASS | Nova appears only in `AGENTS.md` and `docs/research/` reference-boundary files, plus harmless non-project false positives such as trading `continuation` strategy text and npm `es-shim-unscopables`. |
| `find . -maxdepth 3 \( -name '.reference' -o -name 'reference' ... \)` | PASS | No in-repo reference directory found. |
| `ls -ld ../NovaByHorizon ~/Desktop/NovaByHorizon` | PASS | Sibling reference repo exists outside Zulu; no Zulu runtime coupling found. |
| `git check-ignore -v .reference .reference/sample node_modules apps/web/node_modules .venv` | PASS | `.reference/`, dependency directories, and `.venv` are gitignored. |
| `rg -n '^\.reference/|^reference/' .dockerignore .gitignore` | PASS | `.reference/` is ignored by both Git and Docker contexts. |
| Env prefix scan for `ZULU_`, `NEXT_PUBLIC_ZULU_`, `NOVA_`, `HORIZON_` | PASS | Only Zulu env prefixes found. No Nova/Horizon env prefix found. |
| Table/service/name scan over migrations, models, package metadata, services, and UI | PASS | Table names, package names, services, routes, and generated TypeScript contracts use Zulu-native names. |
| Project-description scan for previous-project framing | PASS | No rewrite/fork/derivative/continuation framing found. `migration` matches are database migration references; `continuation` matches are trading setup names. |
| `npm run compose:config` | PASS | Compose config rendered with Zulu service names and Zulu env variables. |
| `npm run security:secrets` | PASS | Secret scan passed. |
| `npm run release:anti-regression` | PASS | All anti-regression checks passed, including live mode disabled by default, tenant isolation, idempotency, stop-loss, options metadata, PolicyGate/RiskGate, kill switch, stale provider data, and accepted-signal durability checks. |
| `npm run migrations:validate` | PASS | Alembic clean upgrade/downgrade validation passed against PostgreSQL. |

Two probe commands failed before correction:

- An initial `rg` command had unsafe shell quoting and zsh rejected it with `unmatched '`. It was rerun with corrected double-quoted regex and passed.
- An initial `python` probe failed because the shell does not expose `python`. It was rerun as `python3` and passed.

## Evidence-Backed Findings

### PASS - Instruction Loading

Severity: None

Evidence:

- `AGENTS.md` exists at repository root.
- Content check returned `True` for all required rule markers:
  - `greenfield`
  - `standalone`
  - `stocks/options-only`
  - `live trading disabled by default`
  - `no accepted signal may silently disappear`

### PASS - Runtime/Public Prior-Project Leakage

Severity: None

Evidence:

- Exact-name scan outside `docs/research/` found no runtime/public Nova, NovaByHorizon, Horizon, old env-prefix, old route, old package, old service, old database table, or old import reference.
- Matches outside research were limited to allowed instruction/ignore surfaces:
  - `AGENTS.md`
  - `.gitignore`
  - `.dockerignore`
  - a Next.js docs URL containing the word `reference`.

### PASS - Reference Isolation

Severity: None

Evidence:

- No in-repo `.reference/` or `reference/` directory exists.
- Sibling `/home/user/Desktop/NovaByHorizon` exists outside the Zulu repository.
- `.reference/` is ignored by `.gitignore` and `.dockerignore`.
- npm workspaces include only `apps/web`.
- Python package discovery includes only `zulu_*` packages from Zulu package/service source roots.
- Pytest discovery lists only Zulu package/service tests and `tests`.
- Docker contexts are rooted at Zulu and `.dockerignore` excludes `.reference/`.

### PASS - Self-Contained Zulu Understanding

Severity: None

Evidence:

- `README.md`, `docs/PROJECT_PRINCIPLES.md`, `docs/SAFETY_AND_COMPLIANCE.md`, architecture docs, operations docs, design docs, release checklist, and runbooks define Zulu without requiring a reference repo.
- `docs/research/nova_reference_lessons.md` states no Nova inspection was performed for the monorepo foundation.

### PASS - No Previous-Project Framing

Severity: None

Evidence:

- Search for previous-project framing found no Zulu description as a rewrite, fork, derivative, compatibility layer, or continuation of another product.
- `migration` hits are database migration docs/scripts.
- `continuation` hits are stocks/options strategy names such as momentum continuation and gap continuation/fade.

## Files Or Modules Requiring Hardening

No High or Critical hardening target was found for greenfield integrity.

Optional Low hardening:

- Consider adding `reference/` to `.gitignore` and `.dockerignore` as a defensive alias, even though project rules require any in-repo reference material to use `.reference/` and no `reference/` directory exists today.

## Tests Missing Or Weak

- No automated test currently asserts that runtime/public files remain free of prior-project names. The scan was performed manually with `rg`.
- No CI job currently enforces `.reference/` isolation and prior-project-name absence as a named greenfield boundary check.
- No docs-link checker is configured, so self-contained docs were verified by inspection and search rather than an automated link audit.

## What Was Not Verified And Why

- Nova repository contents were not inspected. This was intentional because this audit verifies Zulu independence and no implementation from Nova was needed.
- `npm run check:py`, `npm run check`, and `npm run release:verify` were not run because `npm run check:py` invokes `npm run format:py`, which runs `uv run ruff format .` and may rewrite production code. The prompt explicitly prohibited production-code modification.
- Full Docker image build was not rerun for this audit because the question was greenfield boundary and instruction loading; `npm run compose:config` was sufficient to validate deployment naming/context without mutating images.

## Recommended Matching Hardening Prompt

Add an automated greenfield-boundary CI gate that:

- scans runtime/public files for forbidden prior-project names, namespaces, paths, and env prefixes;
- allows Nova references only in `AGENTS.md` and `docs/research/`;
- checks `.reference/` is ignored by Git and Docker;
- verifies npm, Python, pytest, mypy, and Docker discovery settings do not include reference directories;
- fails CI on any runtime/public prior-project leakage.

## Final Determination

GO.

Zulu has a documented greenfield boundary, Codex instructions are present and loaded, no runtime/public leakage from previous projects was found, and reference-only material is safely outside the repository or ignored when using `.reference/`.
