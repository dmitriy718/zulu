from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from zulu_contracts import ComponentHealth, HealthResponse
from zulu_observability import configure_logging, get_logger

from zulu_api.auth import UserRole, UserSession, current_session, redact_token, require_role
from zulu_api.billing import BillingProvider, FixtureBillingProvider
from zulu_api.platform import (
    AutomationEnvironment,
    AutomationSettings,
    BrokerConnectionStatus,
    KillSwitchRequest,
    PageParams,
    PlanChangeRequest,
    PlanChangeResult,
    PlanStatus,
    PlatformStore,
    ProductMode,
    SignalAcknowledgment,
    SignalDetail,
    SignalSummary,
    TenantSettings,
    signal_detail,
)
from zulu_api.security import (
    InMemoryRateLimiter,
    RequestSecurityMiddleware,
    redact_headers,
    validate_safe_fetch_url,
    validate_webhook_signature,
)
from zulu_api.settings import Settings, get_settings


class PaginatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[dict[str, Any]]
    next_cursor: str | None = None


class TenantSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    risk_disclosure_acknowledged: bool | None = None
    provider_data_disclaimer_acknowledged: bool | None = None


class AutomationSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment: AutomationEnvironment
    paper_enabled: bool = True
    shadow_enabled: bool = False
    live_enabled: bool = False
    risk_envelope_id: str = Field(min_length=1, max_length=120)


class WebhookResult(BaseModel):
    accepted: bool
    provider: str


class SafeUrlCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=1000)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    logger = get_logger("zulu.api")

    app = FastAPI(
        title="Zulu API",
        version="0.1.0",
        description="HTTP API and auth boundary for Zulu.",
    )
    app.add_middleware(RequestSecurityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
    )
    app.state.platform_store = PlatformStore.fixture()
    app.state.billing_provider = FixtureBillingProvider()
    app.state.rate_limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)

    def store() -> PlatformStore:
        return cast(PlatformStore, app.state.platform_store)

    def billing() -> BillingProvider:
        return cast(BillingProvider, app.state.billing_provider)

    def limiter() -> InMemoryRateLimiter:
        return cast(InMemoryRateLimiter, app.state.rate_limiter)

    def tenant_context(
        tenant_id: Annotated[str, Path(min_length=1)],
        session: UserSession = Depends(current_session),
    ) -> UserSession:
        if session.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
        return session

    def page_params(
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        cursor: Annotated[str | None, Query(max_length=120)] = None,
    ) -> PageParams:
        return PageParams(limit=limit, cursor=cursor)

    def require_automation_plan(tenant_id: str, platform: PlatformStore) -> PlanStatus:
        plan = platform.subscriptions[tenant_id]
        if ProductMode.AUTOMATION_STATION not in plan.allowed_modes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Automation Station is not enabled for this subscription",
            )
        return plan

    def request_id(request: Request) -> str:
        return str(getattr(request.state, "request_id", "req_unknown"))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, _exc: Exception) -> Response:
        return Response(
            content='{"detail":"internal server error"}',
            status_code=500,
            media_type="application/json",
        )

    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        logger.info("health_check", service="api")
        return HealthResponse(service="api", status="ok")

    @app.get("/readyz", response_model=HealthResponse)
    def readyz() -> HealthResponse:
        components = [
            ComponentHealth(
                name="live_trading_gate",
                status="ok",
                detail=f"live trading is {app_settings.live_trading_gate_summary}",
            ),
            ComponentHealth(
                name="database_configuration",
                status="ok" if app_settings.database_url else "error",
                detail="database URL is configured",
            ),
            ComponentHealth(
                name="redis_configuration",
                status="ok" if app_settings.redis_url else "error",
                detail="redis URL is configured",
            ),
        ]
        status_value = (
            "ok" if all(component.status == "ok" for component in components) else "error"
        )
        return HealthResponse(service="api", status=status_value, components=components)

    @app.get("/auth/session")
    def auth_session(session: UserSession = Depends(current_session)) -> dict[str, str]:
        return {
            "tenant_id": session.tenant_id,
            "user_id": session.user_id,
            "role": session.role.value,
            "token": redact_token(session.token_id),
        }

    @app.get("/auth/me")
    def user_profile(session: UserSession = Depends(current_session)) -> dict[str, str]:
        return {
            "tenant_id": session.tenant_id,
            "user_id": session.user_id,
            "role": session.role.value,
        }

    @app.get("/tenants/{tenant_id}/settings", response_model=TenantSettings)
    def tenant_settings(
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> TenantSettings:
        return platform.tenant_settings[session.tenant_id]

    @app.patch("/tenants/{tenant_id}/settings", response_model=TenantSettings)
    def update_tenant_settings(
        patch: TenantSettingsPatch,
        request: Request,
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> TenantSettings:
        require_role(session, {UserRole.OWNER, UserRole.ADMIN})
        current = platform.tenant_settings[session.tenant_id]
        updated = current.model_copy(update=patch.model_dump(exclude_none=True))
        platform.tenant_settings[session.tenant_id] = updated
        platform.append_audit(
            tenant_id=session.tenant_id,
            actor_id=session.user_id,
            action="tenant_settings.update",
            decision="accepted",
            correlation_id=request_id(request),
            details={"headers": str(redact_headers(dict(request.headers)))},
        )
        return updated

    @app.get("/tenants/{tenant_id}/subscription", response_model=PlanStatus)
    def subscription_status(
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> PlanStatus:
        return platform.subscriptions[session.tenant_id]

    @app.post("/tenants/{tenant_id}/subscription/plan-change", response_model=PlanChangeResult)
    def plan_change(
        body: PlanChangeRequest,
        request: Request,
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
        billing_provider: BillingProvider = Depends(billing),
        rate_limiter: InMemoryRateLimiter = Depends(limiter),
    ) -> PlanChangeResult:
        require_role(session, {UserRole.OWNER, UserRole.ADMIN})
        rate_limiter.check(f"billing:{session.tenant_id}:{session.user_id}")
        result = billing_provider.request_plan_change(
            tenant_id=session.tenant_id,
            request=body,
            production_mode=app_settings.env == "production",
        )
        platform.append_audit(
            tenant_id=session.tenant_id,
            actor_id=session.user_id,
            action="subscription.plan_change_requested",
            decision="accepted" if result.accepted else "blocked",
            correlation_id=request_id(request),
            details={
                "target_plan": body.target_plan.value,
                "billing_reference": result.billing_reference,
            },
        )
        return result

    @app.get("/tenants/{tenant_id}/signals")
    def list_signals(
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
        page: PageParams = Depends(page_params),
    ) -> PaginatedResponse:
        signals = platform.signals.get(session.tenant_id, [])[: page.limit]
        return PaginatedResponse(items=[signal.model_dump(mode="json") for signal in signals])

    @app.get("/tenants/{tenant_id}/signals/{signal_id}", response_model=SignalDetail)
    def get_signal(
        signal_id: str,
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> SignalDetail:
        for signal in platform.signals.get(session.tenant_id, []):
            if signal.signal_id == signal_id:
                return signal_detail(signal)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="signal not found")

    @app.post("/tenants/{tenant_id}/signals/{signal_id}/ack", response_model=SignalSummary)
    def acknowledge_signal(
        signal_id: str,
        body: SignalAcknowledgment,
        request: Request,
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
        rate_limiter: InMemoryRateLimiter = Depends(limiter),
    ) -> SignalSummary:
        require_role(session, {UserRole.OWNER, UserRole.ADMIN, UserRole.TRADER})
        rate_limiter.check(f"signal_ack:{session.tenant_id}:{session.user_id}")
        for idx, signal in enumerate(platform.signals.get(session.tenant_id, [])):
            if signal.signal_id == signal_id:
                updated = signal.model_copy(update={"acknowledged": body.acknowledged})
                platform.signals[session.tenant_id][idx] = updated
                platform.append_audit(
                    tenant_id=session.tenant_id,
                    actor_id=session.user_id,
                    action="signal.acknowledged",
                    decision="accepted",
                    correlation_id=request_id(request),
                    details={"signal_id": signal_id, "client_request_id": body.client_request_id},
                )
                return updated
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="signal not found")

    @app.get("/tenants/{tenant_id}/market/weather")
    def market_weather(session: UserSession = Depends(tenant_context)) -> dict[str, str]:
        return {
            "tenant_id": session.tenant_id,
            "regime": "balanced",
            "data_disclaimer": "Provider data may be delayed or incomplete.",
        }

    @app.get("/tenants/{tenant_id}/market/headlines")
    def headlines(session: UserSession = Depends(tenant_context)) -> PaginatedResponse:
        return PaginatedResponse(
            items=[
                {
                    "tenant_id": session.tenant_id,
                    "ticker": "MSFT",
                    "title": "Fixture headline with provider metadata",
                    "verified": False,
                    "data_disclaimer": "Headline metadata may be incomplete.",
                }
            ]
        )

    @app.get("/tenants/{tenant_id}/policy/status", response_model=HealthResponse)
    def policy_status(session: UserSession = Depends(tenant_context)) -> HealthResponse:
        return HealthResponse(service="policy", status="ok")

    @app.get("/tenants/{tenant_id}/risk/status", response_model=HealthResponse)
    def risk_status(session: UserSession = Depends(tenant_context)) -> HealthResponse:
        return HealthResponse(service="risk", status="ok")

    @app.get("/tenants/{tenant_id}/automation/settings", response_model=AutomationSettings)
    def automation_settings(
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> AutomationSettings:
        require_automation_plan(session.tenant_id, platform)
        return platform.automation_settings[session.tenant_id]

    @app.patch("/tenants/{tenant_id}/automation/settings", response_model=AutomationSettings)
    def update_automation_settings(
        patch: AutomationSettingsPatch,
        request: Request,
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
        rate_limiter: InMemoryRateLimiter = Depends(limiter),
    ) -> AutomationSettings:
        require_role(session, {UserRole.OWNER, UserRole.ADMIN})
        plan = require_automation_plan(session.tenant_id, platform)
        rate_limiter.check(f"automation:{session.tenant_id}:{session.user_id}")
        if patch.live_enabled and not plan.live_trading_allowed:
            raise HTTPException(status_code=403, detail="live automation is not allowed by plan")
        updated = platform.automation_settings[session.tenant_id].model_copy(
            update=patch.model_dump()
        )
        platform.automation_settings[session.tenant_id] = updated
        platform.append_audit(
            tenant_id=session.tenant_id,
            actor_id=session.user_id,
            action="automation.settings_update",
            decision="accepted",
            correlation_id=request_id(request),
            details={
                "environment": patch.environment.value,
                "live_enabled": str(patch.live_enabled),
            },
        )
        return updated

    @app.get("/tenants/{tenant_id}/broker/status", response_model=BrokerConnectionStatus)
    def broker_status(
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> BrokerConnectionStatus:
        require_automation_plan(session.tenant_id, platform)
        return platform.broker_connections[session.tenant_id]

    @app.post("/tenants/{tenant_id}/paper-trading/enable")
    def enable_paper_trading(
        request: Request,
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> AutomationSettings:
        require_role(session, {UserRole.OWNER, UserRole.ADMIN})
        require_automation_plan(session.tenant_id, platform)
        updated = platform.automation_settings[session.tenant_id].model_copy(
            update={"paper_enabled": True, "environment": AutomationEnvironment.PAPER}
        )
        platform.automation_settings[session.tenant_id] = updated
        platform.append_audit(
            tenant_id=session.tenant_id,
            actor_id=session.user_id,
            action="paper_trading.enable",
            decision="accepted",
            correlation_id=request_id(request),
            details={},
        )
        return updated

    @app.get("/tenants/{tenant_id}/execution/orders")
    def order_lifecycle(
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> PaginatedResponse:
        require_automation_plan(session.tenant_id, platform)
        return PaginatedResponse(items=[])

    @app.get("/tenants/{tenant_id}/positions")
    def positions(
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> PaginatedResponse:
        require_automation_plan(session.tenant_id, platform)
        return PaginatedResponse(items=[])

    @app.get("/tenants/{tenant_id}/learning/model-registry")
    def model_registry(session: UserSession = Depends(tenant_context)) -> PaginatedResponse:
        return PaginatedResponse(items=[])

    @app.get("/tenants/{tenant_id}/audit-log")
    def audit_log(
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> PaginatedResponse:
        require_role(
            session,
            {UserRole.OWNER, UserRole.ADMIN, UserRole.OPERATOR, UserRole.SUPPORT_READONLY},
        )
        events = platform.audit_events.get(session.tenant_id, [])
        return PaginatedResponse(items=[event.model_dump(mode="json") for event in events])

    @app.get("/tenants/{tenant_id}/incidents")
    def incidents(
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
    ) -> PaginatedResponse:
        require_role(
            session,
            {UserRole.OWNER, UserRole.ADMIN, UserRole.OPERATOR, UserRole.SUPPORT_READONLY},
        )
        records = platform.incidents.get(session.tenant_id, [])
        return PaginatedResponse(items=[incident.model_dump(mode="json") for incident in records])

    @app.post("/tenants/{tenant_id}/kill-switches")
    def create_kill_switch(
        body: KillSwitchRequest,
        request: Request,
        session: UserSession = Depends(tenant_context),
        platform: PlatformStore = Depends(store),
        rate_limiter: InMemoryRateLimiter = Depends(limiter),
    ) -> dict[str, str]:
        require_role(session, {UserRole.OWNER, UserRole.ADMIN, UserRole.OPERATOR})
        rate_limiter.check(f"kill_switch:{session.tenant_id}:{session.user_id}")
        record = body.model_dump()
        platform.kill_switches.setdefault(session.tenant_id, []).append(record)
        platform.append_audit(
            tenant_id=session.tenant_id,
            actor_id=session.user_id,
            action="kill_switch.create",
            decision="accepted",
            correlation_id=request_id(request),
            details=record,
        )
        return record

    @app.get("/tenants/{tenant_id}/admin/review")
    def admin_review(session: UserSession = Depends(tenant_context)) -> dict[str, str]:
        require_role(session, {UserRole.OWNER, UserRole.ADMIN, UserRole.OPERATOR})
        return {"tenant_id": session.tenant_id, "queue": "operator_review", "status": "open"}

    @app.post("/webhooks/billing", response_model=WebhookResult)
    async def billing_webhook(request: Request) -> WebhookResult:
        payload = await request.body()
        validate_webhook_signature(
            payload=payload,
            signature=request.headers.get("x-zulu-signature"),
            secret="fixture_webhook_secret",
        )
        return WebhookResult(accepted=True, provider="fixture")

    @app.post("/security/safe-url-check")
    def safe_url_check(
        body: SafeUrlCheck,
        _session: UserSession = Depends(current_session),
    ) -> dict[str, bool]:
        validate_safe_fetch_url(body.url)
        return {"safe": True}

    return app


app = create_app()
