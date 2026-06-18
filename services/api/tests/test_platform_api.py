from __future__ import annotations

from fastapi.testclient import TestClient
from zulu_api import create_app
from zulu_api.settings import Settings

OWNER = {"Authorization": "Bearer token-owner"}
ADMIN = {"Authorization": "Bearer token-admin"}
TRADER = {"Authorization": "Bearer token-trader"}
VIEWER = {"Authorization": "Bearer token-viewer"}
OPERATOR = {"Authorization": "Bearer token-operator"}
OTHER = {"Authorization": "Bearer token-other"}


def test_auth_session_redacts_token() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/auth/session", headers=OWNER)

    assert response.status_code == 200
    assert response.json()["token"] == "toke...[REDACTED]"


def test_tenant_isolation_hides_cross_tenant_resources() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/tenants/tenant_2/signals", headers=OWNER)

    assert response.status_code == 404


def test_viewer_cannot_update_tenant_settings() -> None:
    client = TestClient(create_app(Settings()))

    response = client.patch(
        "/tenants/tenant_1/settings",
        headers=VIEWER,
        json={"display_name": "Blocked"},
    )

    assert response.status_code == 403


def test_owner_can_update_tenant_settings_and_audit_is_redacted() -> None:
    client = TestClient(create_app(Settings()))

    response = client.patch(
        "/tenants/tenant_1/settings",
        headers={**OWNER, "X-Request-ID": "req_settings", "X-CSRF-Token": "secret"},
        json={"display_name": "Zulu Updated"},
    )
    audit = client.get("/tenants/tenant_1/audit-log", headers=OWNER)

    assert response.status_code == 200
    assert response.json()["display_name"] == "Zulu Updated"
    assert audit.status_code == 200
    assert "secret" not in str(audit.json())
    assert "[REDACTED]" in str(audit.json())


def test_signal_station_plan_cannot_access_automation_controls() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/tenants/tenant_2/automation/settings", headers=OTHER)

    assert response.status_code == 403
    assert "Automation Station" in response.json()["detail"]


def test_subscription_plan_change_uses_fixture_billing_locally() -> None:
    client = TestClient(create_app(Settings(env="local")))

    response = client.post(
        "/tenants/tenant_1/subscription/plan-change",
        headers=ADMIN,
        json={"target_plan": "automation_live", "idempotency_key": "idem_plan_001"},
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["status"] == "fixture_plan_change_recorded"


def test_subscription_plan_change_does_not_fake_production_billing_success() -> None:
    client = TestClient(create_app(Settings(env="production")))

    response = client.post(
        "/tenants/tenant_1/subscription/plan-change",
        headers=ADMIN,
        json={"target_plan": "automation_live", "idempotency_key": "idem_plan_002"},
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is False
    assert response.json()["status"] == "requires_external_billing_confirmation"


def test_signal_ack_requires_trader_role_and_valid_body() -> None:
    client = TestClient(create_app(Settings()))

    blocked = client.post(
        "/tenants/tenant_1/signals/signal_tenant_1_1/ack",
        headers=VIEWER,
        json={"acknowledged": True, "client_request_id": "ack_0001"},
    )
    invalid = client.post(
        "/tenants/tenant_1/signals/signal_tenant_1_1/ack",
        headers=TRADER,
        json={"acknowledged": True},
    )
    accepted = client.post(
        "/tenants/tenant_1/signals/signal_tenant_1_1/ack",
        headers=TRADER,
        json={"acknowledged": True, "client_request_id": "ack_0001"},
    )

    assert blocked.status_code == 403
    assert invalid.status_code == 422
    assert accepted.status_code == 200
    assert accepted.json()["acknowledged"] is True


def test_live_automation_requires_live_plan() -> None:
    client = TestClient(create_app(Settings()))

    response = client.patch(
        "/tenants/tenant_1/automation/settings",
        headers=ADMIN,
        json={
            "environment": "live",
            "paper_enabled": True,
            "shadow_enabled": True,
            "live_enabled": True,
            "risk_envelope_id": "risk_default",
        },
    )

    assert response.status_code == 403
    assert "live automation" in response.json()["detail"]


def test_kill_switch_is_operator_control_and_rate_limited() -> None:
    client = TestClient(create_app(Settings()))
    payload = {"scope": "ticker", "target": "MSFT", "reason": "operator pause"}

    first = client.post("/tenants/tenant_1/kill-switches", headers=OPERATOR, json=payload)
    second = client.post("/tenants/tenant_1/kill-switches", headers=OPERATOR, json=payload)
    third = client.post("/tenants/tenant_1/kill-switches", headers=OPERATOR, json=payload)
    fourth = client.post("/tenants/tenant_1/kill-switches", headers=OPERATOR, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert fourth.status_code == 429


def test_cookie_auth_requires_csrf_token() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get(
        "/auth/me",
        headers=OWNER,
        cookies={"session_token": "cookie-session"},
    )

    assert response.status_code == 403


def test_billing_webhook_requires_signature() -> None:
    client = TestClient(create_app(Settings()))
    payload = b'{"event":"plan.updated"}'

    rejected = client.post("/webhooks/billing", content=payload)
    accepted = client.post(
        "/webhooks/billing",
        headers={"X-Zulu-Signature": "test-signature-24-cret"},
        content=payload,
    )

    assert rejected.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["accepted"] is True


def test_ssrf_protection_rejects_private_url() -> None:
    client = TestClient(create_app(Settings()))

    response = client.post(
        "/security/safe-url-check",
        headers=OWNER,
        json={"url": "http://127.0.0.1/admin"},
    )

    assert response.status_code == 400
    assert "unsafe" in response.json()["detail"]


def test_secure_headers_and_request_id_are_present() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/auth/me", headers={**OWNER, "X-Request-ID": "req_test"})

    assert response.headers["X-Request-ID"] == "req_test"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_openapi_schema_generation_includes_platform_routes() -> None:
    client = TestClient(create_app(Settings()))

    schema = client.get("/openapi.json").json()

    assert "/tenants/{tenant_id}/signals" in schema["paths"]
    assert "/tenants/{tenant_id}/automation/settings" in schema["paths"]
    assert "/tenants/{tenant_id}/audit-log" in schema["paths"]
