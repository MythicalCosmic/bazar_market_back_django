from dataclasses import dataclass, fields
from typing import Optional


UNSET = object()


@dataclass(frozen=True)
class CreateCategoryDTO:
    name_uz: str
    name_ru: str = ""
    image: str = ""
    parent_id: Optional[int] = None
    sort_order: int = 0
    is_active: bool = True


@dataclass(frozen=True)
class UpdateCategoryDTO:
    name_uz: object = UNSET
    name_ru: object = UNSET
    image: object = UNSET
    parent_id: object = UNSET
    sort_order: object = UNSET
    is_active: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
