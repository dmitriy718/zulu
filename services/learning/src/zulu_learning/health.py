from zulu_contracts import ComponentHealth, HealthResponse


def service_health() -> HealthResponse:
    return HealthResponse(
        service="learning",
        status="ok",
        components=[
            ComponentHealth(
                name="model_promotion",
                status="degraded",
                detail="no model is promoted in local defaults",
            )
        ],
    )
