from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

SENSITIVE_DETAIL_KEYS = {
    "account_id",
    "api_key",
    "broker_credential",
    "credential",
    "ip",
    "private_hostname",
    "token",
}


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"audit_{uuid4().hex}")
    tenant_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str = Field(min_length=1)
    details: dict[str, str] = Field(default_factory=dict)


def build_audit_event(
    *,
    tenant_id: str,
    actor_id: str,
    action: str,
    decision: str,
    correlation_id: str,
    details: dict[str, str] | None = None,
) -> AuditEvent:
    sanitized_details = {
        key: value
        for key, value in (details or {}).items()
        if key.lower() not in SENSITIVE_DETAIL_KEYS
    }
    return AuditEvent(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        decision=decision,
        correlation_id=correlation_id,
        details=sanitized_details,
    )
