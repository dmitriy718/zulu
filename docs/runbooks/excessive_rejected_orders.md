# Excessive Rejected Orders Runbook

1. Check `broker.errors`, `policy.blocks`, and `risk.blocks`.
2. Compare broker rejection reasons with local order request validation.
3. Pause affected strategy, ticker, model, or tenant route with a kill switch.
4. Confirm idempotency prevents duplicate broker requests.
5. Review recent risk envelope changes and broker adapter responses.
6. Reopen routing only after a paper-mode validation pass.
