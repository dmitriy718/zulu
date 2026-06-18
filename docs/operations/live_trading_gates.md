# Live Trading Gates

Live trading is disabled by default.

## Required Gates

Live broker execution requires all of:

- Tenant subscription mode allows live automation.
- User has automation permission.
- User explicitly approved the signal.
- Instrument is allowed by policy.
- Live environment is selected.
- Tenant live trading is explicitly enabled.
- Risk limits explicitly allow live execution.
- PolicyGate approves.
- RiskGate approves.
- No active system, tenant, user, ticker, strategy, model, or broker kill switch applies.
- No critical active incident exists.
- Broker adapter is explicitly enabled.
- Broker credential reference exists.
- Broker request has an idempotency key.
- Audit context exists before broker call.

If any gate is ambiguous, execution must fail closed.

## Operator Controls

Operators must be able to halt execution by:

- System kill switch.
- Tenant kill switch.
- User kill switch.
- Ticker kill switch.
- Strategy kill switch.
- Model kill switch.
- Broker kill switch.
- Critical incident mode.

## Broker Credentials

Credentials must never be hardcoded. Runtime code should use credential references only and redact secrets, account IDs, tokens, and sensitive host details from logs and audit payloads.

## Reconciliation

Live execution cannot be considered complete until broker orders are reconciled or unresolved discrepancies are tied to incidents.
