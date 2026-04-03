from dataclasses import dataclass, fields
from typing import Optional


UNSET = object()


@dataclass(frozen=True)
class CreateDeliveryZoneDTO:
    name: str
    polygon: dict
    delivery_fee: str
    min_order: str = "0"
    estimated_minutes: Optional[int] = None
    is_active: bool = True
    sort_order: int = 0


@dataclass(frozen=True)
class UpdateDeliveryZoneDTO:
    name: object = UNSET
    polygon: object = UNSET
    delivery_fee: object = UNSET
    min_order: object = UNSET
    estimated_minutes: object = UNSET
    is_active: object = UNSET
    sort_order: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
