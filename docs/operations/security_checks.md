# Security Checks

Release candidates run:

```bash
npm run security:audit
npm run security:secrets
```

`security:audit` runs npm dependency audit and `uv pip check`. `security:secrets` scans repository text for committed secret-like values while allowing documented local fixture tokens and development placeholders.

Production secrets must come from environment variables or a secret manager. No broker credential, provider key, payment key, session token, or private account identifier may be committed.
