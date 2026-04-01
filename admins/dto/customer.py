from dataclasses import dataclass, fields
from typing import Optional

UNSET = object()


@dataclass(frozen=True)
class UpdateCustomerDTO:
    first_name: object = UNSET
    last_name: object = UNSET
    phone: object = UNSET
    language: object = UNSET
    telegram_id: object = UNSET
    is_active: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
