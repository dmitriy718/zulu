# Product Mission

Zulu provides trading intelligence and automation for stocks and options only.

## Modes

- Signal Station: receive deeply filtered, contextualized trade signals.
- Automation Station: route approved signals into a strictly risk-governed execution engine.

## Operating Principles

- Production-ready beats prototype.
- Correctness beats speed.
- Risk controls beat automation.
- Auditability beats hidden magic.
- Explicit failures beat silent failures.
- Verified work beats claimed work.
- Deterministic contracts beat loose JSON.
- Bounded autonomy beats unsafe self-modification.

## Safety Requirements

Every accepted trade signal must either become a durable execution attempt or a durable terminal rejection with a reason.

Every automated execution path must pass PolicyGate and RiskGate before any broker adapter call.

Live trading must be disabled by default and impossible without explicit environment, tenant, user, and policy gates.
