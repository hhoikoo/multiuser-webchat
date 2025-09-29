import argparse
import logging
import os
from pathlib import Path

from aiohttp import web

from server.ws import install_ws_router
from server.redis import RedisManager, install_redis_manager

logger = logging.getLogger(__name__)


STATIC_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "static"


async def on_startup(app: web.Application) -> None:
    redis_manager: RedisManager = app["redis_manager"]
    logger.info("Connecting to Redis...")
    await redis_manager.connect()
    logger.info("Redis connected! Establishing pubsub connection...")
    await redis_manager.start_listen()
    logger.info("The server is now ready to listen to Redis messages!")


async def on_cleanup(app: web.Application) -> None:
    redis_manager: RedisManager = app["redis_manager"]
    logger.info("Disconnecting to Redis...")
    await redis_manager.disconnect()
    logger.info("Successfully disconnected to Redis!")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A multiuser webchat application")

    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "localhost"),
        help="Host to bind to (default: localhost, env: HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8080")),
        help="Port to bind to (default: 8080, env: PORT)",
    )
    parser.add_argument(
        "--redis-url",
        type=str,
        default=os.getenv("REDIS_URL", "redis://localhost:6379"),
        help="Redis connection URL (default: redis://localhost:6379, env: REDIS_URL)",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    host = args.host
    port = args.port
    redis_url = args.redis_url

    logger.info("Starting server with address %s:%s...", host, port)
    web.run_app(create_app(redis_url), host=host, port=port)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[{levelname:<8}] {asctime} ({name}.{funcName}) {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    main()
