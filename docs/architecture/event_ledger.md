# Event Ledger

Zulu uses `audit_events`, `order_lifecycle_events`, and `outbox_events` for durable event handling.

## Audit Events

`audit_events` are immutable. The migration installs a PostgreSQL trigger that rejects updates and deletes. Audit rows include tenant, actor, action, entity type, entity id, decision, correlation id, timestamp, and JSON details.

Every clean-signal state transition must be accompanied by an audit event. The database trigger on `clean_signals` requires the session setting `zulu.audit_event_id` to point at an existing audit event for that signal before `acceptance_status` or `terminal_state` can change.

## Clean Signal State

Clean signals are ledger records and cannot be deleted. Terminal states for accepted signals are limited to:

- `delivered_to_signal_station`
- `execution_attempted`
- `policy_rejected`
- `risk_rejected`
- `expired`
- `cancelled_by_user`
- `system_blocked`

The database also checks that option signals reference option metadata, entry and stop fields are present, take-profit and decision trace arrays are non-empty, feature hash/schema values match a stored feature vector, and referenced market data is not expired at signal creation.

## Execution Events

Broker order requests require an idempotency key and have a tenant-scoped uniqueness constraint. Order lifecycle events are immutable and must be either reconciled or tied to a system incident when unresolved.

## Outbox

`outbox_events` provides cross-service event publication support. Events are tenant-scoped, carry aggregate identity, optional idempotency key, payload, creation time, and processing time.
