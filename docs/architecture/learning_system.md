# Learning System

Zulu learning is bounded. It may label outcomes, evaluate changes, run replay, recommend improvements, and prepare promotion records. It may not directly mutate live trading policy, live risk thresholds, live model weights, broker behavior, or production prompts.

## Inputs

Learning inputs include:

- Executed trades.
- Winning, losing, breakeven, partial-exit, stopped-out, expired, rejected, and skipped signals.
- Near misses.
- User overrides.
- Broker execution failures.
- Reconciliation incidents.
- Provider outages.
- Market weather regime changes.

## Labels

The service stores contract-compatible `TradeOutcomeLabel` and `NearMissLabel` records with richer durable detail records.

Trade outcome details include final P/L, max favorable excursion, max adverse excursion, TP levels reached, stop-loss status, entry-trigger status, expiry status, market regime at entry/exit, data limitations, execution quality notes, and rejection/skip reason where applicable.

Near-miss details include whether entry fired, whether the signal expired, TP/stop conditions, market regime before/after, data limitations, execution notes, and rejection/skip reason.

## Replay

Replay runs historical signals through current PolicyGate and RiskGate logic and compares old versus new decisions.

Replay requires:

- Data availability timestamp.
- No-lookahead validation.
- Explicit dataset split: training, validation, test, or shadow.
- Deterministic context factories in tests.

Replay reports are stored and do not alter live policy or risk controls.

## Model Registry

Model registry records wrap contract `ModelManifest` and `ModelEvaluationReport` objects with learning metadata:

- Status: candidate, shadow, paper, approved, deprecated, blocked.
- Training data window.
- Excluded data windows.
- Calibration report.
- Known weaknesses.
- Allowed asset types.
- Allowed strategy types.

## Failure Analysis

The failure-pattern analyzer identifies recurring data, execution, and regime issues from labels. The bounded loop converts those findings into proposed improvements and evaluation tasks only.

## Bounded Autonomy

The learning loop sets `live_mutation_attempted=false` and has no code path to change live policy, risk limits, model weights, broker adapters, or production prompts.
