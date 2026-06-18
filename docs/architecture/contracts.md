# Domain Contracts

Zulu domain contracts live in `packages/contracts/src/zulu_contracts/domain.py` and are mirrored for the web app in `apps/web/lib/contracts.ts`.

## Contract Rules

- Contracts reject unknown fields.
- Timestamps must be timezone-aware.
- Money, prices, scores, and quantities use decimal-safe strings or `Decimal` values.
- Asset scope is stocks and options only.
- Finite states are enums, not free-form strings.

## Backbone Objects

The canonical contract set covers market data, option contracts, headlines, market weather, feature vectors, strategy candidates, clean signals, policy/risk decisions, execution intents, broker order requests, order lifecycle events, positions, outcome labels, model manifests, model evaluations, user overrides, system incidents, audit events, and outbox events.

`CleanSignalV1` is the central Signal Station object. It requires stop loss, entry zone, entry trigger, take-profit levels, sizing hint, contextual explanations, model lineage, feature schema version, feature hash, market weather, market data, and decision trace.

## CleanSignalV1 Invariants

- Option signals require validated option contract metadata.
- Stock signals must not carry option contract metadata.
- Market data must not be expired when the signal is created.
- Feature vectors must not be empty.
- `feature_schema_version` must match the feature vector schema.
- `feature_hash` must match the feature vector content hash.
- Signal expiry must be after creation time.

## Database Mapping

API persistence models live in `services/api/src/zulu_api/data/models.py`. The initial migration creates the corresponding tables, tenant indexes, idempotency constraints, JSONB context fields, decimal columns, and database checks for core invariants.

Cross-service events use `outbox_events`; immutable compliance records use `audit_events`.
