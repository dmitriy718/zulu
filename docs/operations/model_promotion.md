# Model Promotion

Model and scoring-policy promotion requires explicit gates. A model cannot move toward live use because a learning job recommends it.

## Required Promotion Gates

Promotion requires all stages:

1. Candidate evaluation.
2. Shadow mode.
3. Paper mode.
4. Documented evaluation report.
5. Risk review record.
6. Explicit promotion event.
7. Rollback plan.

## Registry Statuses

Supported statuses are:

- `candidate`
- `shadow`
- `paper`
- `approved`
- `deprecated`
- `blocked`

Live use requires a model to pass through evaluation and paper mode first. Promotion to approved status requires an evaluation report, risk review record, promotion event, rollback plan, actor, timestamp, and audit event id.

## Safety Rules

Promotion records do not mutate live systems by themselves. Deployment still requires separate controlled rollout, audit logging, and live trading gates.

Rollback plans must identify the previous approved scoring policy or model and the operational trigger for rollback.

## Operational Checks

Run:

```bash
uv run pytest services/learning/tests
npm run check:py
```

Review replay reports for no-lookahead verification and split coverage before using evaluation results in promotion review.
