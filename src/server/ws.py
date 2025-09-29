from __future__ import annotations

from enum import Enum, auto
import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aiohttp import web, WSMsgType, WSMessage, WSCloseCode
import asyncio

from server.redis import ChatMessage, RedisManager


class PeerStatus(Enum):
    OK = auto()
    CLOSED = auto()
    TIMEOUT = auto()
    INTERNAL_ERROR = auto()


class WSMessageRouter:
    def __init__(self, redis_manager: RedisManager) -> None:
        self.clients: set[web.WebSocketResponse] = set()
        self.redis = redis_manager

        self.redis.set_message_handler(self._broadcast_to_local_peers)

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
            obj: ChatMessage = json.loads(data)
            assert isinstance(obj, dict) and "text" in obj
        except Exception:
            # Drop garbage input instead of crashing the room.
            # TODO: Handle errors more gracefully.
            return

        await self.redis.publish_message(obj)

    async def _broadcast_to_local_peers(self, message: ChatMessage) -> None:
        payload = json.dumps(message)

        # Snapshotting the clients set is necessary here, as during await a
        # client can disconnect, causing a mutation of the clients set, which
        # will cause the iteration to fail.
        clients_snapshot = tuple(self.clients)

        broadcast_results = await asyncio.gather(
            *(self._send_to_peer(peer, payload) for peer in clients_snapshot)
        )

        for peer, result in zip(clients_snapshot, broadcast_results):
            if result != PeerStatus.OK:
                self.clients.discard(peer)

    async def _send_to_peer(
        self, peer: web.WebSocketResponse, payload: str
    ) -> PeerStatus:
        if peer.closed:
            return PeerStatus.CLOSED

        try:
            await asyncio.wait_for(peer.send_str(payload), timeout=0.25)
        except TimeoutError:
            asyncio.create_task(
                peer.close(
                    code=WSCloseCode.GOING_AWAY,
                    message=b"Send timeout",
                )
            )
            return PeerStatus.TIMEOUT
        except Exception:
            # TODO: Hard-exit for unexpected error?
            asyncio.create_task(
                peer.close(
                    code=WSCloseCode.INTERNAL_ERROR,
                    message=b"Unknown internal error",
                )
            )
            return PeerStatus.INTERNAL_ERROR

        return PeerStatus.OK


def install_ws_router(app: web.Application, redis_manager: RedisManager) -> None:
    router = WSMessageRouter(redis_manager)
    app["ws_router"] = router
    app.router.add_get("/ws", router.handler)
