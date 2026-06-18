# Project Principles

## Product Mission

Zulu helps users evaluate stocks and options trade opportunities through contextual signals and, where explicitly authorized, risk-governed automation.

The product has two modes:

- Signal Station for filtered signal review.
- Automation Station for approved signal handling through policy, risk, audit, and execution controls.

## Non-Goals

- Crypto, forex, futures, and gambling-oriented products.
- Claims of profit, certainty, flawless performance, or market-beating outcomes.
- Autonomous live trading without explicit environment, tenant, user, and policy gates.
- Hidden execution behavior that cannot be audited.
- Loose JSON contracts where deterministic schemas are required.

## Architecture Principles

- Keep contracts deterministic and versioned where external or cross-service boundaries exist.
- Prefer explicit state machines for signal, approval, rejection, execution-attempt, and audit flows.
- Separate signal analysis, policy checks, risk checks, broker adapters, and audit storage.
- Fail closed on missing policy, risk, identity, tenant, credential, market-data, or audit prerequisites.
- Choose boring, maintainable infrastructure over novelty.

## Bounded Autonomy Principles

- Automation may act only inside declared tenant, user, account, instrument, strategy, and risk limits.
- Human override must be available for automated execution paths.
- Live automation must require explicit opt-in and remain off by default.
- The system must never modify its own risk, policy, or execution boundaries without a reviewed change.

## Data Integrity Principles

- Accepted signals must have durable terminal state: execution attempt or rejected with reason.
- Broker-bound requests require idempotency keys.
- Audit events must describe who or what initiated an action, when it happened, what gates passed, and what decision was made.
- Simulated, delayed, fixture, and live data must be distinguishable in storage and user-visible contexts.

## User Trust Principles

- Be clear that outputs are informational and not personalized financial advice.
- Surface risk disclosures near signal review, automation enablement, and order-related actions.
- Avoid urgency, certainty, or performance-guarantee language.
- Make failures visible and actionable instead of silently retrying indefinitely.
