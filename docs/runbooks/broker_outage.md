# Broker Outage Runbook

1. Activate broker kill switch for the affected broker.
2. Confirm no broker adapter calls proceed without PolicyGate, RiskGate, idempotency, and audit context.
3. Reconcile known pending orders.
4. Mark unresolved orders with incidents.
5. Keep live trading disabled or halted until broker status is verified.
6. Record operator notes and tenant impact.
