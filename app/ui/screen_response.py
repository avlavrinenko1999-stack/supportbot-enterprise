from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ScreenResponse:
    text: str
    reply_markup: Any | None = None
    delete_user_message: bool = True
    message_kwargs: dict[str, Any] = field(default_factory=dict)
