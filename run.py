import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn_kwargs: dict = {
        "host": settings.api_host,
        "port": settings.api_port,
        "reload": False,
    }
    if settings.api_root_path:
        uvicorn_kwargs["root_path"] = settings.api_root_path
    uvicorn.run("app.main:app", **uvicorn_kwargs)


if __name__ == "__main__":
    main()
