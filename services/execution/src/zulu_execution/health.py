from zulu_contracts import ComponentHealth, HealthResponse


def service_health() -> HealthResponse:
    return HealthResponse(
        service="execution",
        status="ok",
        components=[
            ComponentHealth(
                name="live_broker_adapters",
                status="degraded",
                detail="live broker adapters are disabled in local defaults",
            )
        ],
    )
