# Signal Delivery

Signal delivery is outbox-backed. Signal Intelligence does not fire-and-forget accepted signals.

## Signal Station

When a clean signal passes quality gates:

- The signal is persisted as accepted.
- A `clean_signal.accepted` outbox event is written.
- A `signal_station.signal_delivered` outbox event is written.
- The signal transitions to `delivered_to_signal_station`.
- An audit event records acceptance and terminal transition.

An accepted signal cannot be deleted. Cancellation or failure must be represented as a terminal transition with a reason.

## Automation Station

Automation routing is a review hook, not broker execution.

Signal Intelligence may route a clean signal to Automation Station only through PolicyGate:

- If PolicyGate rejects, the terminal state is `policy_rejected`.
- If PolicyGate approves, the outbox event is `automation_station.policy_approved_for_risk_review`.
- The payload explicitly records that no broker execution was attempted.

RiskGate and broker adapters are later execution-layer responsibilities.

## Outbox Rules

Outbox events require tenant scope, aggregate identity, event type, payload, creation time, and idempotency key.

Duplicate tenant/idempotency-key pairs are rejected. Consumers should mark events processed only after successful delivery.

## Operational Checks

Run signal delivery checks with:

```bash
uv run pytest services/signal-intelligence/tests/test_signal_pipeline.py
uv run pytest services/signal-intelligence/tests
npm run check:py
```

Review audit/outbox events whenever a signal is accepted, rejected, delivered, or routed for automation review.
