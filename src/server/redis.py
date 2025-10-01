from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as redis
from aiohttp import web

from server.models import ChatMessage, json_dumps, json_loads

logger = logging.getLogger(__name__)


MessageHandler = Callable[[ChatMessage], Awaitable[None]]


class RedisManager:
    CHANNEL = "chat:messages"

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.client: redis.Redis | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._message_handler: MessageHandler | None = None

    async def connect(self) -> None:
        if self.client:
            # TODO: Change to a warning and just return instead?
            raise RuntimeError("Attempting to connnect to Redis client twice!")

        self.client = redis.Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
            url=self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task

        if self.client:
            await self.client.aclose()

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._message_handler = handler

    async def publish_message(self, message: ChatMessage) -> None:
        if self.client is None:
            raise RuntimeError("Redis client not connected!")

        payload = json_dumps(message)
        await self.client.publish(self.CHANNEL, payload)  # pyright: ignore[reportUnknownMemberType]

    async def start_listen(self) -> None:
        if not self.client:
            raise RuntimeError("Redis client not connected!")

        self._listener_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self) -> None:
        assert self.client

        try:
            async with self.client.pubsub() as pubsub:  # pyright: ignore[reportUnknownMemberType]
                await pubsub.subscribe(self.CHANNEL)  # pyright: ignore[reportUnknownMemberType]

                async for message in pubsub.listen():  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
                    if message["type"] == "message":
                        try:
                            data = json_loads(message["data"])  # pyright: ignore[reportUnknownArgumentType]
                            if self._message_handler:
                                await self._message_handler(data)
                        except ValueError:
                            logger.exception(
                                "Failed to parse message with data %s!",
                                message["data"],  # pyright: ignore[reportUnknownArgumentType]
                            )
                        except Exception:
                            logger.exception(
                                "Unknown exception occured while receiving message %s.",
                                message,  # pyright: ignore[reportUnknownArgumentType]
                            )
                    elif message["type"] == "subscribe":
                        logger.debug(
                            "Subscribe message received. message=%s",
                            message,  # pyright: ignore[reportUnknownArgumentType]
                        )
                    else:
                        logger.warning(
                            "Unknown message type %s! message=%s",
                            message["type"],  # pyright: ignore[reportUnknownArgumentType]
                            message,  # pyright: ignore[reportUnknownArgumentType]
                        )
        except asyncio.CancelledError as exc:
            logger.info("Client listener is cancelled.")
            raise exc
        except Exception:
            logger.exception("Unknown exception occured during listening loop.")
            return


def install_redis_manager(app: web.Application, redis_url: str) -> RedisManager:
    redis_manager = RedisManager(redis_url)
    app["redis_manager"] = redis_manager
    return redis_manager
