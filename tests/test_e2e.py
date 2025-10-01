import asyncio
import json
import time
from collections.abc import Awaitable, Callable

from aiohttp import web
from aiohttp.client_ws import ClientWebSocketResponse
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from server.models import ChatMessage, json_dumps
from server.ws import WSMessageRouter

MessageHandler = Callable[[ChatMessage], Awaitable[None]]


class MockRedisManager:
    def __init__(self, redis_url: str = "redis://fake") -> None:
        self.redis_url = redis_url
        self.client = None
        self._listener_task = None
        self._message_handler: MessageHandler | None = None
        self._published_messages: list[ChatMessage] = []

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._message_handler = handler

    async def publish_message(self, message: ChatMessage) -> None:
        self._published_messages.append(message)
        if self._message_handler:
            await self._message_handler(message)

    async def start_listen(self) -> None:
        pass

    def get_published_messages(self) -> list[ChatMessage]:
        return self._published_messages.copy()

    def clear_published_messages(self) -> None:
        self._published_messages.clear()


class TestWebSocketE2E(AioHTTPTestCase):
    async def get_application(self) -> web.Application:
        app = web.Application()

        # Install mock Redis manager
        mock_redis = MockRedisManager()
        app["redis_manager"] = mock_redis

        # Install WebSocket router manually
        router = WSMessageRouter(mock_redis)  # type: ignore[arg-type]
        app["ws_router"] = router
        app.router.add_get("/ws", router.handler)

        return app

    @unittest_run_loop
    async def test_two_clients_can_connect_and_message(self) -> None:
        # Create two WebSocket clients
        session1 = await self.client.ws_connect("/ws")
        session2 = await self.client.ws_connect("/ws")

        # Verify both connections are established
        self.assertIsInstance(session1, ClientWebSocketResponse)
        self.assertIsInstance(session2, ClientWebSocketResponse)
        self.assertFalse(session1.closed)
        self.assertFalse(session2.closed)

        # Prepare test message
        test_message = ChatMessage(
            text="Hello from client 1!", type="message", ts=int(time.time() * 1000)
        )

        # Client 1 sends a message
        await session1.send_str(json_dumps(test_message))

        # Both clients should receive the message (fan-out behavior)
        # Give some time for the message to propagate
        await asyncio.sleep(0.1)

        # Check that client 1 receives the message
        msg1 = await session1.receive()
        received_data1 = json.loads(msg1.data)

        # Check that client 2 receives the message
        msg2 = await session2.receive()
        received_data2 = json.loads(msg2.data)

        # Verify both clients received the same message
        self.assertEqual(received_data1, received_data2)
        self.assertEqual(received_data1["text"], test_message.text)
        self.assertEqual(received_data1["type"], test_message.type)
        self.assertEqual(received_data1["ts"], test_message.ts)

        # Verify the message was published to Redis (mocked)
        redis_manager = self.app["redis_manager"]
        published_messages = redis_manager.get_published_messages()
        self.assertEqual(len(published_messages), 1)
        self.assertEqual(published_messages[0].text, test_message.text)

        # Clean up
        await session1.close()
        await session2.close()

    @unittest_run_loop
    async def test_multiple_messages_between_clients(self) -> None:
        # Create two WebSocket clients
        session1 = await self.client.ws_connect("/ws")
        session2 = await self.client.ws_connect("/ws")

        redis_manager = self.app["redis_manager"]
        redis_manager.clear_published_messages()

        # Send multiple messages from different clients
        messages = [
            ChatMessage(text="Message 1 from client 1", type="message", ts=1001),
            ChatMessage(text="Message 2 from client 2", type="message", ts=1002),
            ChatMessage(text="Message 3 from client 1", type="message", ts=1003),
        ]

        # Client 1 sends first message
        await session1.send_str(json_dumps(messages[0]))
        await asyncio.sleep(0.1)

        # Client 2 sends second message
        await session2.send_str(json_dumps(messages[1]))
        await asyncio.sleep(0.1)

        # Client 1 sends third message
        await session1.send_str(json_dumps(messages[2]))
        await asyncio.sleep(0.1)

        # Verify all messages were published to Redis
        published_messages = redis_manager.get_published_messages()
        self.assertEqual(len(published_messages), 3)

        for i, published in enumerate(published_messages):
            self.assertEqual(published.text, messages[i].text)
            self.assertEqual(published.ts, messages[i].ts)

        # Each client should have received all 3 messages
        received_count_client1 = 0
        received_count_client2 = 0

        # Collect all messages from both clients
        try:
            while received_count_client1 < 3:  # noqa: PLR2004
                await asyncio.wait_for(session1.receive(), timeout=0.5)
                received_count_client1 += 1
        except TimeoutError:
            pass

        try:
            while received_count_client2 < 3:  # noqa: PLR2004
                await asyncio.wait_for(session2.receive(), timeout=0.5)
                received_count_client2 += 1
        except TimeoutError:
            pass

        self.assertEqual(received_count_client1, 3)
        self.assertEqual(received_count_client2, 3)

        # Clean up
        await session1.close()
        await session2.close()

    @unittest_run_loop
    async def test_invalid_message_handling(self) -> None:
        # Create WebSocket client
        session = await self.client.ws_connect("/ws")

        # Send invalid JSON
        await session.send_str("invalid json")
        await asyncio.sleep(0.1)

        # Server should not crash and Redis should not receive the message
        redis_manager = self.app["redis_manager"]
        published_messages = redis_manager.get_published_messages()
        self.assertEqual(len(published_messages), 0)

        # Connection should still be open
        self.assertFalse(session.closed)

        # Send valid message to verify connection is still working
        valid_message = ChatMessage(text="Valid message", type="message", ts=1004)
        await session.send_str(json_dumps(valid_message))
        await asyncio.sleep(0.1)

        # This should work
        published_messages = redis_manager.get_published_messages()
        self.assertEqual(len(published_messages), 1)
        self.assertEqual(published_messages[0].text, "Valid message")

        # Clean up
        await session.close()
