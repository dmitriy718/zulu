# Auth And Tenants

Zulu uses tenant-scoped authorization for all product and control endpoints.

## Roles

Supported roles:

- `owner`
- `admin`
- `trader`
- `viewer`
- `operator`
- `support-readonly`

Owners and admins can update tenant settings, subscription intent, and automation settings. Traders can acknowledge signals. Operators can review incidents and create kill switches. Support-readonly can read audit and incident context without write permissions.

## Tenant Isolation

Every user-owned resource must carry tenant identity. API requests must authenticate a session and match the session tenant to the path tenant. Cross-tenant access is reported as not found.

## Audit

Sensitive operations create audit events:

- Tenant settings changes.
- Subscription plan-change requests.
- Signal acknowledgments.
- Automation settings changes.
- Paper trading enablement.
- Kill switch creation.

Audit details redact secrets, credentials, tokens, session values, and account identifiers.

## Session Logging

Tokens and session values must not be logged. API session responses expose only redacted token identifiers.

## Cookie Auth

When cookie auth is used, requests must include a valid CSRF token. The local fixture expects `X-CSRF-Token: csrf-ok`.
