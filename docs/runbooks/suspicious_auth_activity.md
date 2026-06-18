# Suspicious Auth Activity Runbook

1. Rate-limit or revoke suspicious sessions.
2. Review request IDs, tenant IDs, role usage, and failed authorization patterns.
3. Confirm cross-tenant access returns not found.
4. Rotate impacted session secrets through the auth provider.
5. Record incident and audit event.
6. Review logs for redaction before sharing externally.
