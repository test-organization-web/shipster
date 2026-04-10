"""ASGI entrypoint and local runner. Application wiring lives in `shipster.platform`."""

import os

import uvicorn

from shipster.platform.app import create_app
from shipster.platform.settings import get_global_settings

app = create_app()


def main() -> None:
    settings = get_global_settings()
    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        log_config=None,
        log_level=settings.log_level.lower(),
        access_log=settings.access_log,
    )


if __name__ == "__main__":
    main()
