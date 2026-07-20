import os

from aiohttp import web

from web.application import create_application


def run() -> None:
    web.run_app(
        create_application(),
        host=os.getenv("WEB_HOST", "0.0.0.0"),
        port=int(os.getenv("WEB_PORT", "8080")),
        print=None,
    )


if __name__ == "__main__":
    run()
