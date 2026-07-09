import json
from pathlib import Path

from aiogram.types import Message

REGISTRY_PATH = Path("/opt/supportbot_v2/data/chat_message_registry.json")


class ChatRegistry:
    LIMIT = 200

    @staticmethod
    def _load() -> dict[str, list[int]]:
        if not REGISTRY_PATH.exists():
            return {}
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def _save(data: dict[str, list[int]]) -> None:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def chat_key(message: Message) -> str:
        return str(message.chat.id)

    @staticmethod
    def ids_for(message: Message) -> list[int]:
        return list(ChatRegistry._load().get(ChatRegistry.chat_key(message), []))

    @staticmethod
    def remember(message: Message) -> None:
        data = ChatRegistry._load()
        key = ChatRegistry.chat_key(message)

        ids = data.get(key, [])
        if message.message_id not in ids:
            ids.append(message.message_id)

        data[key] = ids[-ChatRegistry.LIMIT:]
        ChatRegistry._save(data)

    @staticmethod
    def clear(message: Message) -> None:
        data = ChatRegistry._load()
        data[ChatRegistry.chat_key(message)] = []
        ChatRegistry._save(data)
