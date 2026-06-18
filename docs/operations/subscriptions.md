# Subscriptions

Subscriptions gate product modes.

## Plans

`signal_basic`:

- Signal Station only.
- No automation settings.
- No broker controls.
- No execution controls.

`automation_paper`:

- Signal Station.
- Automation Station.
- Paper and shadow automation controls.
- Live trading not allowed.

`automation_live`:

- Signal Station.
- Automation Station.
- Paper, shadow, and live controls subject to all live gates.

## Billing Provider

The API uses a billing provider abstraction. Local tests use a fixture billing provider.

Production mode must not fake billing success. Plan-change requests in production return an external-confirmation-required result unless a real billing provider is explicitly configured.

## Upgrade And Downgrade Hooks

Plan-change requests are idempotent and audited. They do not directly alter broker credentials, live trading settings, risk limits, or tenant policy.

## Safety

Subscription capability is necessary but not sufficient for execution. Automation still requires PolicyGate, RiskGate, live trading gates where applicable, idempotency, and audit context.
