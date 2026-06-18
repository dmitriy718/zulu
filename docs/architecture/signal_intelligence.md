# Signal Intelligence

Signal Intelligence turns validated market context into explainable `CleanSignalV1` records for Signal Station and Automation Station review.

## Pipeline

The production pipeline sequence is:

1. Build normalized market context through provider interfaces.
2. Generate a `CanonicalFeatureVectorV1`.
3. Generate modular `StrategyCandidate` records.
4. Score candidates.
5. Apply calibration hooks when real calibration data exists.
6. Apply quality gates.
7. Attach market weather and headline context.
8. Build `CleanSignalV1`.
9. Persist acceptance and decision trace.
10. Publish durable outbox events.
11. Deliver to Signal Station or route to Automation Station through PolicyGate.

The pipeline uses shared contracts rather than service-local loose JSON.

## Strategy Modules

Initial deterministic modules are:

- Momentum continuation.
- VWAP reclaim/reject.
- Volatility expansion.
- Gap continuation/fade.
- Options unusual activity when options data supports it.
- Pullback to support/resistance.

Each module may return one candidate or no candidate. Candidate IDs are deterministic from tenant, ticker, setup, direction, asset type, and feature hash.

## Scoring

`BaselineCandidateScorer` is deterministic and marks `model_mode` as `baseline`. It does not claim a trained model exists.

Confidence, risk, and quality are separate:

- Confidence uses trend, VWAP, relative volume, market weather, and headline pressure.
- Risk uses spread, volatility, risk-off weather, and options liquidity where applicable.
- Quality combines confidence and inverse risk.

Calibration is a hook. It must not record calibration metrics until evaluated labeled data exists.

## Quality Gates

Signals are blocked for:

- Missing stop loss.
- Missing entry zone or trigger.
- Stale market data.
- Empty feature vector.
- Unsupported asset type.
- Missing options metadata for option signals.
- Missing market weather.
- Missing decision trace.
- Invalid take-profit ladder.
- Expired signal timestamp.
- Nonsensical risk/reward.
- Confidence, quality, or risk outside configured acceptance bounds.

Contract validation catches many invalid shapes before quality gates run. Quality gates add signal-specific acceptance floors.

## Explanations

Signals include:

- What got attention.
- Setup type.
- Upside thesis.
- Downside risk.
- Catalyst/headline context.
- Market weather effect.
- Entry conditions.
- Take-profit ladder.
- Stop loss.
- Invalidation conditions.
- Confidence explanation.
- Risk explanation.
- Data limitations.

Explanations must not promise outcomes or imply certainty.

## Durability

Accepted signals are written to a signal ledger and cannot be deleted. They must transition to a contract terminal state. The current handlers use:

- `delivered_to_signal_station` after Signal Station outbox delivery.
- `policy_rejected` when Automation Station PolicyGate rejects.
- `delivered_to_signal_station` when Automation Station PolicyGate approves later risk review; no broker execution is attempted in Signal Intelligence.

Broker execution remains outside this layer. Any future broker-bound path must pass PolicyGate, RiskGate, idempotency, and audit requirements before a broker adapter call.
