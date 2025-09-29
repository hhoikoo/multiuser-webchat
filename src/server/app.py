import os
from pathlib import Path

from aiohttp import web

from server.ws import install_ws_router
from server.redis import RedisManager, install_redis_manager


STATIC_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "static"


async def on_startup(app: web.Application) -> None:
    redis_manager: RedisManager = app["redis_manager"]
    await redis_manager.connect()
    await redis_manager.start_listen()


async def on_cleanup(app: web.Application) -> None:
    redis_manager: RedisManager = app["redis_manager"]
    await redis_manager.disconnect()


async def healthz(_: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def index(_: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_RESOURCES_DIR / "index.html")


def create_app(redis_url: str) -> web.Application:
    app = web.Application()
    app.add_routes(
        [
            web.get("/", index),
            web.get("/healthz", healthz),
            web.static("/static", STATIC_RESOURCES_DIR),
        ]
    )

    redis_manager = install_redis_manager(app, redis_url)
    install_ws_router(app, redis_manager)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app


def main() -> None:
    # TODO: Add argparse stuff?
    port = int(os.getenv("PORT", "8080"))
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    web.run_app(create_app(redis_url), host="localhost", port=port)


if __name__ == "__main__":
    main()
