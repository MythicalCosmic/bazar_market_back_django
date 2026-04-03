from dataclasses import dataclass, fields
from typing import Optional


UNSET = object()


@dataclass(frozen=True)
class CreateBannerDTO:
    image: str
    title: str = ""
    link_type: str = "none"
    link_value: str = ""
    sort_order: int = 0
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: bool = True


@dataclass(frozen=True)
class UpdateBannerDTO:
    title: object = UNSET
    image: object = UNSET
    link_type: object = UNSET
    link_value: object = UNSET
    sort_order: object = UNSET
    starts_at: object = UNSET
    expires_at: object = UNSET
    is_active: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
