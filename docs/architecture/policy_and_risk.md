# Policy And Risk

Zulu execution authority is intentionally split into PolicyGate and RiskGate.

## PolicyGate

PolicyGate decides whether a clean signal may be delivered, routed, blocked, or escalated for automation review. It checks:

- Tenant subscription mode.
- User automation permission.
- Paper, shadow, or live environment.
- Stocks/options asset support.
- Signal and market data freshness.
- Market session status.
- Restricted tickers and option contracts.
- Model manifest status.
- Feature schema status.
- Data quality status.
- Market weather risk state.
- Incident mode and kill switch state.
- Compliance copy presence.
- User override status.

PolicyGate fails closed. Live automation additionally requires live subscription mode and explicit live enablement.

## RiskGate

RiskGate decides whether a policy-approved signal may become an execution intent. It checks:

- Max risk per trade.
- Max daily and weekly loss.
- Max open positions.
- Max ticker exposure.
- Max sector exposure when sector data exists.
- Options-specific limits.
- Liquidity and spread limits.
- Position sizing.
- Stop-loss presence.
- Take-profit ladder validity.
- Duplicate signal/order protection.
- Pending open and close conflicts.
- Day-trading restrictions when configured.
- Explicit live environment enablement.

RiskGate uses signal contracts plus an execution risk context. It never calls broker adapters.

## Kill Switches

Kill switches are evaluated before broker-bound work. Supported scopes are:

- System.
- Tenant.
- User.
- Ticker.
- Strategy.
- Model.
- Broker.

Critical active incidents block live trading.

## Execution Boundary

No signal, model, UI action, background job, or admin command may call a broker adapter directly. Execution must flow through:

`CleanSignalV1 -> PolicyGate -> RiskGate -> ExecutionIntent -> BrokerOrderRequest -> BrokerAdapter -> OrderLifecycleEvent -> Reconciliation`
