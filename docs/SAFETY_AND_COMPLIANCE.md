# Safety And Compliance

## Scope

Zulu supports stocks and options only. Crypto, forex, futures, and gambling/casino framing are out of scope.

## Positioning

Zulu is an educational and informational trading intelligence product. It must not present outputs as personalized financial advice. UI, docs, fixtures, and examples must avoid promises of profit, certainty, flawless operation, or market-beating performance.

## Human Override And Live Gates

Live trading is disabled by default. It must require explicit environment, tenant, user, and policy gates before any live broker adapter call is possible.

Automation must provide a human override path. Users must be able to disable automation for a tenant, user, account, strategy, or instrument scope.

## Audit Logging

Audit events are required for signal acceptance, terminal rejection, policy decisions, risk decisions, execution attempts, broker adapter requests, broker adapter responses, automation enablement, automation disablement, and credential lifecycle events.

Audit logs must include actor, tenant, timestamp, decision, relevant policy/risk version, and correlation identifiers. Do not place secrets, raw tokens, broker credentials, user PII, private hostnames, private IPs, or sensitive full stack traces in audit logs.

## Broker Credentials

Broker credentials must be encrypted at rest, redacted in logs, scoped by tenant and user, and never exposed to clients after creation. Credential checks must fail closed when scope, owner, policy, or environment is ambiguous.

## Tenant Isolation

Tenant identity must be explicit in persisted records, authorization checks, audit events, queues, jobs, and broker-bound workflows. Cross-tenant reads, writes, cache keys, idempotency keys, and background jobs must be prevented by design and covered by tests when those layers exist.

## Risk Disclosure Placement

Risk disclosures must appear near signal review, automation enablement, order preview, broker connection, and live-trading activation flows. Disclosures must be visible before a user enables live automation or approves broker-bound actions.
