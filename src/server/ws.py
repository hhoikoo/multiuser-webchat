from __future__ import annotations

from enum import Enum, auto
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aiohttp import web, WSMsgType, WSMessage, WSCloseCode
import asyncio

from server.redis import ChatMessage, RedisManager

logger = logging.getLogger(__name__)


class PeerStatus(Enum):
    OK = auto()
    CLOSED = auto()
    TIMEOUT = auto()
    INTERNAL_ERROR = auto()


TIMEOUT = 0.25


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
                        logger.info("Received message %s of type TEXT.", message)
                        await self._handle_text(message)
                    case WSMsgType.ERROR:
                        logger.error("Received an Error message %s!", message)
                        break
                    case _ as type:
                        # TODO: Handle more WSMsgType.
                        logger.warning(
                            "Unknown message type %s! message=%s", type, message
                        )
                        break
        return ws

    @asynccontextmanager
    async def _initialize_ws(
        self, req: web.Request
    ) -> AsyncGenerator[web.WebSocketResponse]:
        ws = web.WebSocketResponse(heartbeat=25)  # keep-alive
        logger.info("Connecting to WebSocket at address %s...", req.url)
        await ws.prepare(req)
        logger.info("Connection established to %s!", req.url)
        self.clients.add(ws)

        try:
            yield ws
        finally:
            self.clients.discard(ws)
            logger.info("Disconnecting from WebSocket...")
            await ws.close()
            logger.info("Successfully disconnected.")

    async def _handle_text(self, message: WSMessage) -> None:
        data = message.data

        try:
            obj = ChatMessage.from_json(data)
        except ValueError:
            # Drop garbage input instead of crashing the room.
            logger.warning("Failed to parse message %s", data, exc_info=True)
            return
        except Exception:
            logger.exception("Unexpected error while parsing message %s")
            return

        await self.redis.publish_message(obj)

    async def _broadcast_to_local_peers(self, message: ChatMessage) -> None:
        payload = message.to_json()

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
            logger.info("Connection to %s is closed.", peer)
            return PeerStatus.CLOSED

        try:
            await asyncio.wait_for(peer.send_str(payload), timeout=TIMEOUT)
        except TimeoutError:
            logger.warning(
                "Connection to %s timed out after %s seconds while sending message %s.",
                peer,
                TIMEOUT,
                payload,
            )
            asyncio.create_task(
                peer.close(
                    code=WSCloseCode.GOING_AWAY,
                    message=b"Send timeout",
                )
            )
            return PeerStatus.TIMEOUT
        except Exception:
            # TODO: Hard-exit for unexpected error?
            logger.exception(
                "Unknown internal error for %s while sending message %s!",
                peer,
                payload,
            )
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
