# Execution And Reconciliation

Execution service owns broker authority after PolicyGate and RiskGate approve a clean signal.

## Authority Flow

`ExecutionAuthorityService` creates:

- Contract `PolicyDecision`.
- Contract `RiskDecision`.
- `ExecutionIntent`.
- `BrokerOrderRequest`.
- `OrderLifecycleEvent`.
- Audit events for policy, risk, request creation, and broker response.

Broker calls require:

- PolicyGate approval.
- RiskGate approval.
- Idempotency key/client order ID.
- Audit event context.

## Broker Adapters

Broker adapters are broker-neutral. The paper adapter is complete enough for local and integration tests and stores deterministic paper order state by idempotency key and broker order ID.

The live adapter is a hard-gated skeleton. It requires:

- Adapter enabled.
- Live environment.
- Explicit live trading enablement.
- Credential reference.

It has no default credentials and no live transport configured.

## Idempotency

Broker requests require an idempotency key. Paper broker submissions return the same response for duplicate idempotent requests. Unknown broker state is not blindly retried.

## Reconciliation

`ReconciliationWorker` compares local lifecycle state with broker adapter status. It handles:

- Filled orders.
- Partial fills.
- Cancelled orders.
- Missing broker status.
- Stale pending orders.
- Duplicate terminal lifecycle states.
- Manual operator reconciliation.

Unresolved discrepancies create `SystemIncident` records and unresolved lifecycle events where applicable.

## Safety Boundary

The execution layer supports stocks and options only. Options execution requires validated option contract metadata before broker request creation.
