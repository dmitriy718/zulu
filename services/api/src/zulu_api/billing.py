from __future__ import annotations

from typing import Protocol

from zulu_api.platform import PlanChangeRequest, PlanChangeResult


class BillingProvider(Protocol):
    def request_plan_change(
        self, *, tenant_id: str, request: PlanChangeRequest, production_mode: bool
    ) -> PlanChangeResult: ...


class FixtureBillingProvider:
    def request_plan_change(
        self, *, tenant_id: str, request: PlanChangeRequest, production_mode: bool
    ) -> PlanChangeResult:
        if production_mode:
            return PlanChangeResult(
                accepted=False,
                status="requires_external_billing_confirmation",
                reason="production billing requires configured provider confirmation",
                billing_reference=f"billing_pending_{tenant_id}_{request.idempotency_key}",
            )
        return PlanChangeResult(
            accepted=True,
            status="fixture_plan_change_recorded",
            reason="fixture billing provider recorded the requested plan change",
            billing_reference=f"fixture_billing_{tenant_id}_{request.idempotency_key}",
        )
