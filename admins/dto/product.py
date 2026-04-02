from dataclasses import dataclass, fields, field
from typing import Optional


UNSET = object()


@dataclass(frozen=True)
class CreateProductDTO:
    category_id: int
    name_uz: str
    unit: str
    price: str
    name_ru: str = ""
    description_uz: str = ""
    description_ru: str = ""
    step: str = "1"
    min_qty: str = "1"
    max_qty: Optional[str] = None
    in_stock: bool = True
    stock_qty: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    is_featured: bool = False
    images: list = field(default_factory=list)


@dataclass(frozen=True)
class UpdateProductDTO:
    category_id: object = UNSET
    name_uz: object = UNSET
    name_ru: object = UNSET
    description_uz: object = UNSET
    description_ru: object = UNSET
    unit: object = UNSET
    price: object = UNSET
    step: object = UNSET
    min_qty: object = UNSET
    max_qty: object = UNSET
    in_stock: object = UNSET
    stock_qty: object = UNSET
    sort_order: object = UNSET
    is_active: object = UNSET
    is_featured: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
