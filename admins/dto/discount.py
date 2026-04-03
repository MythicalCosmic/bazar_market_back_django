from dataclasses import dataclass, fields
from typing import Optional


UNSET = object()


@dataclass(frozen=True)
class CreateDiscountDTO:
    name_uz: str
    type: str
    value: str
    name_ru: str = ""
    max_discount: Optional[str] = None
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: bool = True
    product_ids: list = None
    category_ids: list = None


@dataclass(frozen=True)
class UpdateDiscountDTO:
    name_uz: object = UNSET
    name_ru: object = UNSET
    type: object = UNSET
    value: object = UNSET
    max_discount: object = UNSET
    starts_at: object = UNSET
    expires_at: object = UNSET
    is_active: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
