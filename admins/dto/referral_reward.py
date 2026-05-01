from dataclasses import dataclass, fields
from typing import Optional

UNSET = object()


@dataclass(frozen=True)
class CreateReferralRewardDTO:
    name: str
    type: str  # coupon | free_delivery | bonus_product

    # Coupon
    coupon_type: str = "percent"
    coupon_value: Optional[str] = None
    coupon_max_discount: Optional[str] = None
    coupon_min_order: Optional[str] = None
    coupon_expires_days: int = 30

    # Free delivery
    free_delivery_count: int = 1

    # Bonus product
    bonus_product_id: Optional[int] = None
    bonus_quantity: str = "1"

    is_active: bool = False


@dataclass(frozen=True)
class UpdateReferralRewardDTO:
    name: object = UNSET
    type: object = UNSET
    coupon_type: object = UNSET
    coupon_value: object = UNSET
    coupon_max_discount: object = UNSET
    coupon_min_order: object = UNSET
    coupon_expires_days: object = UNSET
    free_delivery_count: object = UNSET
    bonus_product_id: object = UNSET
    bonus_quantity: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
