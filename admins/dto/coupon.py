from dataclasses import dataclass, fields
from typing import Optional


UNSET = object()


@dataclass(frozen=True)
class CreateCouponDTO:
    code: str
    type: str
    value: str
    min_order: Optional[str] = None
    max_discount: Optional[str] = None
    usage_limit: Optional[int] = None
    per_user_limit: int = 1
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: bool = True


@dataclass(frozen=True)
class UpdateCouponDTO:
    code: object = UNSET
    type: object = UNSET
    value: object = UNSET
    min_order: object = UNSET
    max_discount: object = UNSET
    usage_limit: object = UNSET
    per_user_limit: object = UNSET
    starts_at: object = UNSET
    expires_at: object = UNSET
    is_active: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
