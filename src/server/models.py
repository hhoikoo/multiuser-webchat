import json
import logging
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ChatMessage:
    text: str
    type: str
    ts: int

    @staticmethod
    def from_json(obj_str: str) -> "ChatMessage":
        try:
            obj_json = json.loads(obj_str)
            return ChatMessage(**obj_json)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON string %s!", obj_str)
            raise ValueError from exc
        except TypeError as exc:
            logger.error("Failed to convert %s to a ChatMessage!", obj_str)
            raise ValueError from exc

    def to_json(self) -> str:
        return json.dumps(asdict(self))
