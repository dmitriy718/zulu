from fastapi.testclient import TestClient
from zulu_api import create_app
from zulu_api.settings import Settings

AUTH = {"Authorization": "Bearer token-owner"}


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["service"] == "api"
    assert response.json()["status"] == "ok"


def test_readiness_reports_live_trading_disabled_by_default() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/readyz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert any(
        component["name"] == "live_trading_gate"
        and component["detail"] == "live trading is disabled"
        for component in payload["components"]
    )


def test_product_status_endpoints_require_tenant_auth() -> None:
    client = TestClient(create_app(Settings()))

    unauthenticated = client.get("/tenants/tenant_1/policy/status")
    policy = client.get("/tenants/tenant_1/policy/status", headers=AUTH)
    risk = client.get("/tenants/tenant_1/risk/status", headers=AUTH)

    assert unauthenticated.status_code == 401
    assert policy.status_code == 200
    assert policy.json()["service"] == "policy"
    assert risk.status_code == 200
    assert risk.json()["service"] == "risk"


def test_learning_status_endpoint_is_tenant_scoped() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/tenants/tenant_1/learning/model-registry", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["items"] == []
