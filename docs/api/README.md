# Zulu API

The Zulu API is the platform control boundary for Signal Station and Automation Station.

## Auth Boundary

Local development uses a fixture auth provider behind the same provider interface used for production integration. Requests use:

```text
Authorization: Bearer <token>
```

Fixture tokens are scoped to a tenant and role. Response payloads redact token values.

## Tenant Scope

All product/control endpoints are tenant-scoped under:

```text
/tenants/{tenant_id}/...
```

The authenticated session tenant must match the path tenant. Cross-tenant access returns `404` to avoid resource discovery.

Public endpoints are limited to `/healthz`, `/readyz`, `/openapi.json`, and docs routes.

## Product Modes

Signal Station endpoints expose clean signals, market weather, headlines, and signal acknowledgments.

Automation Station endpoints expose automation settings, broker connection status, paper trading controls, execution/order lifecycle, positions, kill switches, and admin/operator review. Automation Station endpoints require an automation-capable subscription.

## Security Controls

The API adds:

- Request IDs.
- Secure response headers.
- CORS limited to local web origin by default.
- CSRF checks when cookie auth is present.
- Rate limits on sensitive write endpoints.
- HMAC-style fixture validation for billing webhooks.
- SSRF protection for URL validation.
- Redaction for sensitive headers and audit details.
- Generic error responses for unhandled exceptions.

## Compliance Copy

API responses include support for:

- Stocks/options automation risk disclosures.
- Clear distinction between signals and user-directed automation.
- Delayed or incomplete provider data disclaimers.
- Model uncertainty and data-limitation notes.

The API must not promise profit, certainty, flawless behavior, or market-beating outcomes.
