from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlaceOrderDTO:
    address_id: int
    payment_method: str
    coupon_code: Optional[str] = None
    user_note: str = ""
    scheduled_time: Optional[str] = None
