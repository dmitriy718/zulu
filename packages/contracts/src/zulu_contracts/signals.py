from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class AssetClass(StrEnum):
    STOCK = "stock"
    OPTION = "option"


class SignalStatus(StrEnum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXECUTION_ATTEMPTED = "execution_attempted"


class SignalCandidate(BaseModel):
    symbol: str = Field(min_length=1, max_length=12, pattern=r"^[A-Z][A-Z0-9.\-]*$")
    asset_class: AssetClass
    thesis: str = Field(min_length=20, max_length=2000)
    source: str = Field(min_length=1, max_length=120)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidence_score: float = Field(ge=0.0, le=1.0)


class SignalDisposition(BaseModel):
    signal_id: str = Field(min_length=1)
    status: SignalStatus
    reason: str | None = Field(default=None, max_length=500)
    idempotency_key: str | None = Field(default=None, min_length=16, max_length=120)
    audit_event_id: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_terminal_state(self) -> "SignalDisposition":
        if self.status == SignalStatus.REJECTED and not self.reason:
            raise ValueError("rejected signals require a reason")
        if self.status == SignalStatus.EXECUTION_ATTEMPTED:
            if not self.idempotency_key:
                raise ValueError("execution attempts require an idempotency key")
            if not self.audit_event_id:
                raise ValueError("execution attempts require an audit event id")
        return self
