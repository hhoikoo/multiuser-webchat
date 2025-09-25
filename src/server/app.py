from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response


async def healthz(_: Request) -> Response:
    return web.json_response({"ok": True})


async def index(_: Request) -> Response:
    return web.Response(text="bootcamp-webchat up", content_type="text/plain")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/healthz", healthz)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8080)
