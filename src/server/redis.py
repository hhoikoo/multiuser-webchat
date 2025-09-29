from __future__ import annotations

import json
from typing import Awaitable, Callable, TypedDict

import asyncio
import redis.asyncio as redis
from aiohttp import web


class ChatMessage(TypedDict):
    text: str
    type: str
    ts: int


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

        self.client = redis.Redis.from_url(
            url=self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.client:
            await self.client.aclose()

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._message_handler = handler

    async def publish_message(self, message: ChatMessage) -> None:
        if not self.client:
            raise RuntimeError("Redis client not connected!")

        payload = json.dumps(message)
        await self.client.publish(self.CHANNEL, payload)

    async def start_listen(self) -> None:
        if not self.client:
            raise RuntimeError("Redis client not connected!")

        self._listener_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self) -> None:
        assert self.client

        try:
            async with self.client.pubsub() as pubsub:
                await pubsub.subscribe(self.CHANNEL)

                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            if self._message_handler:
                                await self._message_handler(data)
                        except json.JSONDecodeError:
                            # TODO: Log warning for invalid JSON.
                            continue
                        except Exception:
                            # TODO: Log generic warning.
                            continue
                    else:
                        # TODO: Log warning for unknown message type
                        continue
        except asyncio.CancelledError:
            # TODO: Log cancellation before reraising.
            raise
        except Exception:
            # TODO: Log error
            return


def install_redis_manager(app: web.Application, redis_url: str) -> RedisManager:
    redis_manager = RedisManager(redis_url)
    app["redis_manager"] = redis_manager
    return redis_manager
