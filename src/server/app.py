from pathlib import Path

from aiohttp import web


STATIC_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "static"


async def healthz(_: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def index(_: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_RESOURCES_DIR / "index.html")


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes(
        [
            web.get("/", index),
            web.get("/healthz", healthz),
            web.static("/static", STATIC_RESOURCES_DIR),
        ]
    )
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8080)
