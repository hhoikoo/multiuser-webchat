import argparse
import logging
import multiprocessing
import os
import signal
import sys
from pathlib import Path
from types import FrameType

from aiohttp import web

from server.redis import RedisManager, install_redis_manager
from server.ws import WSMessageRouter, install_ws_router

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
    ws_router: WSMessageRouter = app["ws_router"]
    logger.info("Closing all open WebSocket connections...")
    await ws_router.close_all_connections()
    logger.info("Successfully closed all WebSocket connections!")

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


def run_worker(worker_id: int, host: str, port: int, redis_url: str) -> None:
    setup_logging()

    logger.info(f"[Worker {worker_id}] Starting on {host}:{port} (PID: {os.getpid()})")

    app = create_app(redis_url)

    web.run_app(
        app,
        host=host,
        port=port,
        reuse_port=True,
        print=lambda *args: None,  # Suppress aiohttp's startup message per worker
    )


def shutdown_workers(
    processes: list[multiprocessing.Process], timeout: int = 5
) -> None:
    logger.info("Shutting down %d workers...", len(processes))

    for process in processes:
        if process.is_alive():
            process.terminate()

    for process in processes:
        process.join(timeout=timeout)

        if process.is_alive():
            logger.warning(
                "Worker %s didn't stop after %d seconds, killing...",
                timeout,
                process.name,
            )
            process.kill()
            process.join()

    logger.info("All %d workers stopped", len(processes))


def register_signal_handlers(processes: list[multiprocessing.Process]) -> None:
    def signal_handler(signum: int, _: FrameType | None) -> None:
        logger.info("Received signal %d", signum)
        shutdown_workers(processes)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


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

    def positive_integer(value: str) -> int:
        try:
            ivalue = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{value} is not a valid integer") from exc
        if ivalue < 1:
            raise argparse.ArgumentTypeError(f"{value} must be at least 1")
        return ivalue

    parser.add_argument(
        "--workers",
        type=positive_integer,
        default=positive_integer(os.getenv("WORKERS", "1")),
        help="Number of workers (must be at least 1, default: 1, env: WORKERS)",
    )

    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[{levelname:<8}] {asctime} [PID:{process}] ({name}.{funcName}) {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    args = parse_args()
    host: str = args.host
    port: int = args.port
    redis_url: str = args.redis_url
    workers: int = args.workers

    if workers == 1:
        logger.info("Starting server with address %s:%s...", host, port)
        web.run_app(create_app(redis_url), host=host, port=port)
        return

    processes: list[multiprocessing.Process] = []
    for worker_id in range(workers):
        process = multiprocessing.Process(
            target=run_worker,
            args=(worker_id, host, port, redis_url),
            name=f"worker-{worker_id}",
        )
        process.start()
        logger.info("Started worker %d (PID: %d)", worker_id, process.pid)

        processes.append(process)

    register_signal_handlers(processes)

    try:
        for process in processes:
            process.join()

        shutdown_workers(processes)
    except KeyboardInterrupt:
        # Signal handler is already called at this point.
        pass


if __name__ == "__main__":
    setup_logging()
    main()
