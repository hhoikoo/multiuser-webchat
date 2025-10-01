import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import WSCloseCode, WSMessage, WSMsgType

from server.models import ChatMessage, json_dumps
from server.ws import SEND_TIMEOUT, WS_CLOSE_TIMEOUT, PeerStatus, WSMessageRouter

# Test constants
EXPECTED_CALL_COUNT = 2
EXPECTED_CLIENT_COUNT = 2
EXPECTED_SEND_TIMEOUT = 0.25
EXPECTED_WS_CLOSE_TIMEOUT = 2.0


class TestPeerStatus:
    def test_enum_values(self) -> None:
        assert PeerStatus.OK
        assert PeerStatus.CLOSED
        assert PeerStatus.TIMEOUT
        assert PeerStatus.INTERNAL_ERROR


class TestWSMessageRouter:
    @pytest.fixture
    def mock_redis_manager(self) -> MagicMock:
        mock = MagicMock()
        mock.publish_message = MagicMock()
        return mock

    @pytest.fixture
    def ws_router(self, mock_redis_manager: MagicMock) -> WSMessageRouter:
        return WSMessageRouter(mock_redis_manager)

    @pytest.fixture
    def mock_websocket(self) -> AsyncMock:
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.fixture
    def sample_message(self) -> ChatMessage:
        return ChatMessage(text="Test message", type="message", ts=1234567890)

    def test_init(self, mock_redis_manager: MagicMock) -> None:
        router = WSMessageRouter(mock_redis_manager)

        assert router.redis == mock_redis_manager
        assert len(router.clients) == 0
        mock_redis_manager.set_message_handler.assert_called_once()

    async def test_broadcast_to_local_peers(
        self, ws_router: WSMessageRouter, sample_message: ChatMessage
    ) -> None:
        # Add mock clients
        client1 = AsyncMock()
        client1.closed = False
        client2 = AsyncMock()
        client2.closed = False

        ws_router.clients.add(client1)
        ws_router.clients.add(client2)

        with patch.object(ws_router, "_send_to_peer") as mock_send:
            mock_send.return_value = PeerStatus.OK

            await ws_router._broadcast_to_local_peers(sample_message)

            assert mock_send.call_count == EXPECTED_CALL_COUNT
            # Both clients should still be in the set
            assert len(ws_router.clients) == EXPECTED_CLIENT_COUNT

    async def test_broadcast_removes_failed_clients(
        self, ws_router: WSMessageRouter, sample_message: ChatMessage
    ) -> None:
        # Add mock clients
        client1 = AsyncMock()
        client2 = AsyncMock()

        ws_router.clients.add(client1)
        ws_router.clients.add(client2)

        with patch.object(ws_router, "_send_to_peer") as mock_send:
            # Simulate one client failing
            mock_send.side_effect = [PeerStatus.OK, PeerStatus.TIMEOUT]

            await ws_router._broadcast_to_local_peers(sample_message)

            # Failed client should be removed
            assert len(ws_router.clients) == 1
            assert client1 in ws_router.clients
            assert client2 not in ws_router.clients

    async def test_send_to_peer_success(
        self, ws_router: WSMessageRouter, mock_websocket: AsyncMock
    ) -> None:
        result = await ws_router._send_to_peer(mock_websocket, "test payload")

        assert result == PeerStatus.OK
        mock_websocket.send_str.assert_called_once_with("test payload")

    async def test_send_to_peer_closed_connection(
        self, ws_router: WSMessageRouter
    ) -> None:
        closed_ws = AsyncMock()
        closed_ws.closed = True

        result = await ws_router._send_to_peer(closed_ws, "test payload")

        assert result == PeerStatus.CLOSED
        closed_ws.send_str.assert_not_called()

    async def test_send_to_peer_timeout(self, ws_router: WSMessageRouter) -> None:
        timeout_ws = AsyncMock()
        timeout_ws.closed = False
        timeout_ws.send_str.side_effect = TimeoutError()
        timeout_ws.close = AsyncMock()

        result = await ws_router._send_to_peer(timeout_ws, "test payload")

        assert result == PeerStatus.TIMEOUT
        timeout_ws.close.assert_called_once_with(
            code=WSCloseCode.GOING_AWAY,
            message=b"Send timeout",
        )

    async def test_send_to_peer_internal_error(
        self, ws_router: WSMessageRouter
    ) -> None:
        error_ws = AsyncMock()
        error_ws.closed = False
        error_ws.send_str.side_effect = Exception("Test error")
        error_ws.close = AsyncMock()

        result = await ws_router._send_to_peer(error_ws, "test payload")

        assert result == PeerStatus.INTERNAL_ERROR
        error_ws.close.assert_called_once_with(
            code=WSCloseCode.INTERNAL_ERROR,
            message=b"Unknown internal error",
        )

    async def test_handle_text_valid_message(
        self, ws_router: WSMessageRouter, sample_message: ChatMessage
    ) -> None:
        message = WSMessage(
            type=WSMsgType.TEXT, data=json_dumps(sample_message), extra=None
        )

        await ws_router._handle_text(message)

        mock_publish = cast(MagicMock, ws_router.redis.publish_message)
        mock_publish.assert_called_once()
        published_msg = mock_publish.call_args[0][0]
        assert published_msg.text == sample_message.text
        assert published_msg.type == sample_message.type
        assert published_msg.ts == sample_message.ts

    async def test_handle_text_invalid_json(self, ws_router: WSMessageRouter) -> None:
        message = WSMessage(type=WSMsgType.TEXT, data="invalid json", extra=None)

        # Should not raise exception
        await ws_router._handle_text(message)

        # Should not publish anything
        mock_publish = cast(MagicMock, ws_router.redis.publish_message)
        mock_publish.assert_not_called()

    async def test_handle_text_missing_fields(self, ws_router: WSMessageRouter) -> None:
        message = WSMessage(
            type=WSMsgType.TEXT, data='{"text": "missing fields"}', extra=None
        )

        # Should not raise exception
        await ws_router._handle_text(message)

        # Should not publish anything
        mock_publish = cast(MagicMock, ws_router.redis.publish_message)
        mock_publish.assert_not_called()

    async def test_close_all_connections_empty(
        self, ws_router: WSMessageRouter
    ) -> None:
        # Should not raise error when no clients
        await ws_router.close_all_connections()

        assert len(ws_router.clients) == 0

    async def test_close_all_connections_with_clients(
        self, ws_router: WSMessageRouter
    ) -> None:
        # Add mock clients
        client1 = AsyncMock()
        client1.closed = False
        client2 = AsyncMock()
        client2.closed = True  # Already closed

        ws_router.clients.add(client1)
        ws_router.clients.add(client2)

        await ws_router.close_all_connections()

        # Only open client should be closed
        client1.close.assert_called_once_with(
            code=WSCloseCode.GOING_AWAY, message=b"Server shutting down"
        )
        client2.close.assert_not_called()

        # All clients should be cleared
        assert len(ws_router.clients) == 0

    async def test_close_all_connections_timeout(
        self, ws_router: WSMessageRouter
    ) -> None:
        # Add mock client that times out on close
        slow_client = AsyncMock()
        slow_client.closed = False
        slow_client.close.side_effect = asyncio.sleep(10)  # Simulate slow close

        ws_router.clients.add(slow_client)

        # Should complete despite timeout
        await ws_router.close_all_connections()

        assert len(ws_router.clients) == 0

    @patch("server.ws.web.WebSocketResponse")
    async def test_initialize_ws_context_manager(
        self, mock_ws_class: MagicMock, ws_router: WSMessageRouter
    ) -> None:
        mock_ws = AsyncMock()
        mock_ws_class.return_value = mock_ws
        mock_req = MagicMock()

        async with ws_router._initialize_ws(mock_req) as ws:
            assert ws == mock_ws
            assert mock_ws in ws_router.clients
            mock_ws.prepare.assert_called_once_with(mock_req)

        # After context exit, should be removed and closed
        assert mock_ws not in ws_router.clients
        mock_ws.close.assert_called_once()

    def test_constants(self) -> None:
        assert SEND_TIMEOUT == EXPECTED_SEND_TIMEOUT
        assert WS_CLOSE_TIMEOUT == EXPECTED_WS_CLOSE_TIMEOUT
