import uvicorn

from zulu_api.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "zulu_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.env == "local",
    )


if __name__ == "__main__":
    main()
