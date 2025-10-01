import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ChatMessage:
    text: str
    type: str
    ts: int


class ChatMessageEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, ChatMessage):
            return asdict(o)
        return super().default(o)


def chat_message_decoder(obj: dict[str, Any]) -> ChatMessage | dict[str, Any]:
    if {"text", "type", "ts"}.issubset(obj.keys()):
        return ChatMessage(**obj)
    return obj


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, cls=ChatMessageEncoder)


def json_loads(s: str) -> Any:
    return json.loads(s, object_hook=chat_message_decoder)
