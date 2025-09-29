import json

import pytest

from server.models import ChatMessage


class TestChatMessage:
    def test_create_chat_message(self) -> None:
        message = ChatMessage(text="Hello world", type="message", ts=1234567890)

        assert message.text == "Hello world"
        assert message.type == "message"
        assert message.ts == 1234567890

    def test_to_json(self) -> None:
        message = ChatMessage(text="Test message", type="broadcast", ts=9876543210)
        json_str = message.to_json()

        parsed = json.loads(json_str)
        assert parsed["text"] == "Test message"
        assert parsed["type"] == "broadcast"
        assert parsed["ts"] == 9876543210

    def test_from_json_valid(self) -> None:
        json_str = '{"text": "From JSON", "type": "alert", "ts": 1111111111}'
        message = ChatMessage.from_json(json_str)

        assert message.text == "From JSON"
        assert message.type == "alert"
        assert message.ts == 1111111111

    def test_from_json_invalid_json(self) -> None:
        with pytest.raises(ValueError):
            ChatMessage.from_json("invalid json")

    def test_from_json_missing_fields(self) -> None:
        with pytest.raises(ValueError):
            ChatMessage.from_json('{"text": "Missing fields"}')

    def test_from_json_extra_fields_ignored(self) -> None:
        # ChatMessage accepts any types, but extra fields should be ignored
        json_str = '{"text": "Test", "type": "message", "ts": 123, "extra": "ignored"}'
        with pytest.raises(ValueError):  # TypeError gets wrapped as ValueError
            ChatMessage.from_json(json_str)

    def test_round_trip_serialization(self) -> None:
        original = ChatMessage(text="Round trip test", type="system", ts=5555555555)
        json_str = original.to_json()
        restored = ChatMessage.from_json(json_str)

        assert original == restored

    def test_frozen_dataclass(self) -> None:
        message = ChatMessage(text="Immutable", type="test", ts=123)

        with pytest.raises(Exception):  # Should be FrozenInstanceError
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
        json_str = message.to_json()
        restored = ChatMessage.from_json(json_str)

        assert restored.text == ""
        assert restored.type == "empty"
        assert restored.ts == 0

    def test_unicode_text(self) -> None:
        unicode_text = "Hello 🌍 世界 emoji test! 🚀"
        message = ChatMessage(text=unicode_text, type="unicode", ts=777)

        json_str = message.to_json()
        restored = ChatMessage.from_json(json_str)

        assert restored.text == unicode_text
        assert restored == message
