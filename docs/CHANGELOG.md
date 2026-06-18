# Changelog

## 2026-06-18

- Initialized foundational Codex operating rules for the greenfield Zulu project.
- Added project principles, task verification requirements, safety and compliance rules, decision record format, and reference research boundaries.
- Recorded that no production application stack or production dependencies are selected yet.
- Initialized a production monorepo foundation with Next.js web app, FastAPI API, importable Python service packages, shared contracts, policy/risk/observability packages, Docker Compose, and health/status tests.
- Added strict domain contracts, mirrored TypeScript contract types, SQLAlchemy database models, initial Alembic migration, immutable audit/event ledger triggers, migration validation script, and architecture docs.
- Added the market data and context ingestion layer with provider interfaces, deterministic fixture provider, environment-gated provider skeletons, resilience handling, normalizers, market weather classification, canonical feature generation, provider-health docs, and tests.
- Added the Signal Intelligence pipeline with modular deterministic strategies, baseline scoring, quality gates, explanation generation, accepted-signal ledger invariants, durable outbox publishing, Signal Station delivery, PolicyGate-only Automation Station routing, architecture docs, operations docs, and tests.
- Added execution authority with expanded PolicyGate and RiskGate checks, kill switches, broker-neutral paper/live adapters, idempotency, execution intent/order lifecycle creation, reconciliation worker, policy/risk/execution status endpoints, operations docs, and tests.
- Added bounded continuous learning with durable outcome and near-miss labeling, deterministic replay with no-lookahead checks, model registry and evaluation reports, staged promotion workflow, failure-pattern analysis, learning-cycle recommendations, API status endpoints, docs, and tests.
- Added production API/platform control layer with fixture auth provider abstraction, tenant authorization, role checks, subscription gating, billing provider abstraction, Signal Station and Automation Station route groups, audit log access, operator controls, security middleware, OpenAPI validation tests, and operations docs.
- Added the Zulu web mission-control interface with typed fixture/API client boundaries, auth/subscription-aware route context, full primary navigation, Command Center, Signal Station, Automation Station, Market Weather, Decision Ledger, Positions & Orders, Learning Lab, Model Health, Incidents & Controls, Settings, component tests, smoke/e2e coverage, and interface design docs.
- Added release-candidate operations with CI workflow, staging/production deployment templates, environment examples, observability metrics, backup/restore scripts, security and secret-scan commands, production runbooks, final anti-regression script, and release checklist.
- Upgraded the web interface into a darker liquid-glass trading command center with icon-led navigation, floating execution guard, richer signal/gate/weather surfaces, and current UI package verification.
