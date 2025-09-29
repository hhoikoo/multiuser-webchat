import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.models import ChatMessage
from server.redis import RedisManager


class TestRedisManager:
    @pytest.fixture
    def redis_manager(self) -> RedisManager:
        return RedisManager("redis://test:6379")

    @pytest.fixture
    def mock_redis_client(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def sample_message(self) -> ChatMessage:
        return ChatMessage(text="Test message", type="message", ts=1234567890)

    def test_init(self, redis_manager: RedisManager) -> None:
        assert redis_manager.redis_url == "redis://test:6379"
        assert redis_manager.client is None
        assert redis_manager._listener_task is None
        assert redis_manager._message_handler is None

    @patch("server.redis.redis.Redis.from_url")
    async def test_connect(
        self, mock_from_url: MagicMock, redis_manager: RedisManager
    ) -> None:
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        await redis_manager.connect()

        assert redis_manager.client == mock_client
        mock_from_url.assert_called_once_with(
            url="redis://test:6379",
            encoding="utf-8",
            decode_responses=True,
        )

    async def test_connect_twice_raises_error(
        self, redis_manager: RedisManager
    ) -> None:
        redis_manager.client = AsyncMock()  # Simulate already connected

        with pytest.raises(
            RuntimeError, match="Attempting to connnect to Redis client twice!"
        ):
            await redis_manager.connect()

    async def test_disconnect_with_active_task(
        self, redis_manager: RedisManager
    ) -> None:
        # Setup active listener task
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        redis_manager._listener_task = mock_task
        redis_manager.client = AsyncMock()

        await redis_manager.disconnect()

        mock_task.cancel.assert_called_once()

    async def test_disconnect_with_completed_task(
        self, redis_manager: RedisManager
    ) -> None:
        # Setup completed listener task
        mock_task = AsyncMock()
        mock_task.done.return_value = True
        redis_manager._listener_task = mock_task
        redis_manager.client = AsyncMock()

        await redis_manager.disconnect()

        mock_task.cancel.assert_not_called()
        redis_manager.client.aclose.assert_called_once()

    async def test_disconnect_no_client(self, redis_manager: RedisManager) -> None:
        # Should not raise error when no client exists
        await redis_manager.disconnect()

    def test_set_message_handler(self, redis_manager: RedisManager) -> None:
        handler = AsyncMock()
        redis_manager.set_message_handler(handler)

        assert redis_manager._message_handler == handler

    async def test_publish_message(
        self, redis_manager: RedisManager, sample_message: ChatMessage
    ) -> None:
        mock_client = AsyncMock()
        redis_manager.client = mock_client

        await redis_manager.publish_message(sample_message)

        mock_client.publish.assert_called_once_with(
            RedisManager.CHANNEL, sample_message.to_json()
        )

    async def test_publish_message_no_client(
        self, redis_manager: RedisManager, sample_message: ChatMessage
    ) -> None:
        with pytest.raises(RuntimeError, match="Redis client not connected!"):
            await redis_manager.publish_message(sample_message)

    async def test_start_listen(self, redis_manager: RedisManager) -> None:
        mock_client = AsyncMock()
        redis_manager.client = mock_client

        with patch.object(redis_manager, "_listen_loop") as mock_listen_loop:
            await redis_manager.start_listen()

            assert redis_manager._listener_task is not None
            # Need to let the task start
            await asyncio.sleep(0.001)

    async def test_start_listen_no_client(self, redis_manager: RedisManager) -> None:
        with pytest.raises(RuntimeError, match="Redis client not connected!"):
            await redis_manager.start_listen()

    async def test_listen_loop_message_handling(
        self, redis_manager: RedisManager, sample_message: ChatMessage
    ) -> None:
        mock_client = AsyncMock()
        mock_handler = AsyncMock()
        redis_manager.client = mock_client
        redis_manager._message_handler = mock_handler

        # Mock pubsub context manager
        mock_pubsub = AsyncMock()
        mock_client.pubsub.return_value.__aenter__.return_value = mock_pubsub
        mock_client.pubsub.return_value.__aexit__.return_value = None

        # Mock message iteration
        messages = [
            {"type": "subscribe", "data": None},
            {"type": "message", "data": sample_message.to_json()},
        ]
        mock_pubsub.listen.return_value.__aiter__ = lambda self: iter(messages)

        # Run listen loop once and cancel
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(redis_manager._listen_loop(), timeout=0.1)

        mock_pubsub.subscribe.assert_called_once_with(RedisManager.CHANNEL)
        mock_handler.assert_called_once_with(sample_message)

    async def test_listen_loop_invalid_message(
        self, redis_manager: RedisManager
    ) -> None:
        mock_client = AsyncMock()
        redis_manager.client = mock_client

        # Mock pubsub context manager
        mock_pubsub = AsyncMock()
        mock_client.pubsub.return_value.__aenter__.return_value = mock_pubsub
        mock_client.pubsub.return_value.__aexit__.return_value = None

        # Mock invalid message
        messages = [
            {"type": "message", "data": "invalid json"},
        ]
        mock_pubsub.listen.return_value.__aiter__ = lambda self: iter(messages)

        # Should not crash on invalid message
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(redis_manager._listen_loop(), timeout=0.1)

        # Test should complete without raising

    async def test_listen_loop_cancelled(self, redis_manager: RedisManager) -> None:
        mock_client = AsyncMock()
        redis_manager.client = mock_client

        # Mock pubsub that gets cancelled
        mock_pubsub = AsyncMock()
        mock_client.pubsub.return_value.__aenter__.return_value = mock_pubsub
        mock_client.pubsub.return_value.__aexit__.return_value = None

        # Mock listen that raises CancelledError
        async def mock_listen():
            yield {"type": "subscribe", "data": None}
            raise asyncio.CancelledError()

        mock_pubsub.listen.return_value = mock_listen()

        with pytest.raises(asyncio.CancelledError):
            await redis_manager._listen_loop()

    def test_channel_constant(self) -> None:
        assert RedisManager.CHANNEL == "chat:messages"
