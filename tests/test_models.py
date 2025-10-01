import json
from dataclasses import FrozenInstanceError

import pytest

from server.models import ChatMessage, json_dumps, json_loads

# Test constants
SAMPLE_TIMESTAMP_1 = 1234567890
SAMPLE_TIMESTAMP_2 = 9876543210
SAMPLE_TIMESTAMP_3 = 1111111111


class TestChatMessage:
    def test_create_chat_message(self) -> None:
        message = ChatMessage(text="Hello world", type="message", ts=SAMPLE_TIMESTAMP_1)

        assert message.text == "Hello world"
        assert message.type == "message"
        assert message.ts == SAMPLE_TIMESTAMP_1

    def test_to_json(self) -> None:
        message = ChatMessage(
            text="Test message", type="broadcast", ts=SAMPLE_TIMESTAMP_2
        )
        json_str = json_dumps(message)

        parsed = json.loads(json_str)
        assert parsed["text"] == "Test message"
        assert parsed["type"] == "broadcast"
        assert parsed["ts"] == SAMPLE_TIMESTAMP_2

    def test_from_json_valid(self) -> None:
        json_str = (
            f'{{"text": "From JSON", "type": "alert", "ts": {SAMPLE_TIMESTAMP_3}}}'
        )
        message = json_loads(json_str)

        assert message.text == "From JSON"
        assert message.type == "alert"
        assert message.ts == SAMPLE_TIMESTAMP_3

    def test_from_json_invalid_json(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            json_loads("invalid json")

    def test_from_json_missing_fields(self) -> None:
        obj = json_loads('{"text": "Missing fields"}')
        assert not isinstance(obj, ChatMessage)

    def test_from_json_extra_fields_throw_error(self) -> None:
        json_str = '{"text": "Test", "type": "message", "ts": 123, "extra": "ignored"}'
        with pytest.raises(TypeError):
            json_loads(json_str)

    def test_round_trip_serialization(self) -> None:
        original = ChatMessage(text="Round trip test", type="system", ts=5555555555)
        json_str = json_dumps(original)
        restored = json_loads(json_str)

        assert original == restored

    def test_frozen_dataclass(self) -> None:
        message = ChatMessage(text="Immutable", type="test", ts=123)

        with pytest.raises(FrozenInstanceError):
            message.text = "Changed"  # type: ignore[misc]

    def test_keyword_only_constructor(self) -> None:
        # Should work with keywords
        message = ChatMessage(text="KW only", type="test", ts=456)
        assert message.text == "KW only"

        # Should fail with positional args
        with pytest.raises(TypeError):
            ChatMessage("Positional", "test", 789)  # type: ignore[misc]

    def test_empty_text(self) -> None:
        message = ChatMessage(text="", type="empty", ts=0)
        json_str = json_dumps(message)
        restored = json_loads(json_str)

        assert restored.text == ""
        assert restored.type == "empty"
        assert restored.ts == 0

    def test_unicode_text(self) -> None:
        unicode_text = "Hello 🌍 世界 emoji test! 🚀"
        message = ChatMessage(text=unicode_text, type="unicode", ts=777)

        json_str = json_dumps(message)
        restored = json_loads(json_str)

        assert restored.text == unicode_text
        assert restored == message
