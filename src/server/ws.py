from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aiohttp import web, WSMsgType, WSMessage, WSCloseCode
import asyncio


class WSMessageRouter:
    def __init__(self) -> None:
        self.clients: set[web.WebSocketResponse] = set()

    async def handler(self, req: web.Request) -> web.StreamResponse:
        async with self._initialize_ws(req) as ws:
            async for message in ws:
                match message.type:
                    case WSMsgType.TEXT:
                        await self._handle_text(message)
                    case WSMsgType.ERROR:
                        # TODO: Handle error more properly.
                        break
                    case _:
                        # TODO: Handle more WSMsgType.
                        break
        return ws

    @asynccontextmanager
    async def _initialize_ws(
        self, req: web.Request
    ) -> AsyncGenerator[web.WebSocketResponse]:
        ws = web.WebSocketResponse(heartbeat=25)  # keep-alive
        await ws.prepare(req)
        self.clients.add(ws)

        try:
            yield ws
        finally:
            self.clients.discard(ws)
            await ws.close()

    async def _handle_text(self, message: WSMessage) -> None:
        data = message.data

        try:
            obj = json.loads(data)
            assert isinstance(obj, dict) and "text" in obj
        except Exception:
            # Drop garbage input instead of crashing the room.
            # TODO: Handle errors more gracefully.
            return

        # TODO: Use Redis for broadcasting to clients.
        await self._broadcast_local(json.dumps(obj))

    async def _broadcast_local(self, payload: str) -> None:
        clients_to_drop: list[web.WebSocketResponse] = []

        # Snapshotting the clients set is necessary here, as during await a
        # client can disconnect, causing a mutation of the clients set, which
        # will cause the iteration to fail.
        clients_snapshot = tuple(self.clients)
        for peer in clients_snapshot:
            if peer.closed:
                clients_to_drop.append(peer)
                continue

            try:
                # TODO: Use asyncio.gather() to await on many client writes at
                # the same time?
                await asyncio.wait_for(peer.send_str(payload), timeout=0.25)
            except TimeoutError:
                asyncio.create_task(
                    peer.close(
                        code=WSCloseCode.GOING_AWAY,
                        message=b"Send timeout",
                    )
                )
                clients_to_drop.append(peer)
            except Exception:
                # TODO: Hard-exit for unexpected error?
                asyncio.create_task(
                    peer.close(
                        code=WSCloseCode.INTERNAL_ERROR,
                        message=b"Unknown internal error",
                    )
                )
                clients_to_drop.append(peer)

        for peer in clients_to_drop:
            self.clients.discard(peer)


def install_ws_router(app: web.Application) -> None:
    router = WSMessageRouter()
    app["ws_router"] = router
    app.router.add_get("/ws", router.handler)
