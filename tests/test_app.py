from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.app import get_messages, healthz
from server.models import ChatMessage

HTTP_OK = 200
HTTP_INTERNAL_SERVER_ERROR = 500


class TestHealthzEndpoint:
    async def test_healthz_returns_ok(self) -> None:
        mock_request = MagicMock()
        response = await healthz(mock_request)

        assert response.status == HTTP_OK
        assert response.content_type == "application/json"


class TestGetMessagesEndpoint:
    async def test_get_messages_valid_minutes(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.fetch_history = AsyncMock(
            return_value=[
                ChatMessage(text="test1", type="message", ts=1234567890),
                ChatMessage(text="test2", type="message", ts=1234567891),
            ]
        )

        mock_request = MagicMock()
        mock_request.query.get.return_value = "30"
        mock_request.app = {"redis_manager": mock_redis}

        response = await get_messages(mock_request)

        assert response.status == HTTP_OK
        mock_redis.fetch_history.assert_called_once_with(minutes=30)

    async def test_get_messages_invalid_minutes_non_numeric(self) -> None:
        mock_request = MagicMock()
        mock_request.query.get.return_value = "invalid"

        with pytest.raises(web.HTTPBadRequest, match="not a valid integer"):
            await get_messages(mock_request)

    async def test_get_messages_invalid_minutes_negative(self) -> None:
        mock_request = MagicMock()
        mock_request.query.get.return_value = "-1"

        with pytest.raises(web.HTTPBadRequest, match="must be a positive number"):
            await get_messages(mock_request)

    async def test_get_messages_invalid_minutes_too_large(self) -> None:
        mock_request = MagicMock()
        mock_request.query.get.return_value = "2000"

        with pytest.raises(web.HTTPBadRequest, match="cannot be more than 24 hours"):
            await get_messages(mock_request)

    async def test_get_messages_default_minutes(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.fetch_history = AsyncMock(return_value=[])

        mock_request = MagicMock()
        mock_request.query.get.return_value = "30"
        mock_request.app = {"redis_manager": mock_redis}

        await get_messages(mock_request)

        mock_redis.fetch_history.assert_called_once_with(minutes=30)

    async def test_get_messages_redis_error(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.fetch_history = AsyncMock(side_effect=Exception("Redis error"))

        mock_request = MagicMock()
        mock_request.query.get.return_value = "30"
        mock_request.app = {"redis_manager": mock_redis}

        response = await get_messages(mock_request)

        assert response.status == HTTP_INTERNAL_SERVER_ERROR
