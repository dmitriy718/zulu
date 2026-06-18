from zulu_contracts import ComponentHealth, HealthResponse


def service_health() -> HealthResponse:
    return HealthResponse(
        service="signal-intelligence",
        status="ok",
        components=[
            ComponentHealth(
                name="market_data_adapters",
                status="degraded",
                detail="no live market data adapter configured in local defaults",
            )
        ],
    )
