from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CreateNotificationDTO:
    title: str
    body: str
    type: str = "promo"
    channel: str = "telegram"
    payload: Optional[dict] = None


@dataclass(frozen=True)
class BulkNotificationDTO:
    title: str
    body: str
    type: str = "promo"
    channel: str = "telegram"
    payload: Optional[dict] = None
    user_ids: Optional[list] = None
    role: Optional[str] = None
