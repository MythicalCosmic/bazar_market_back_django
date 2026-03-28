from dataclasses import dataclass, fields, asdict
from typing import Optional


UNSET = object()


@dataclass(frozen=True)
class CreateUserDTO:
    username: str
    first_name: str
    last_name: str
    role: str
    password: str
    language: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[int] = None


@dataclass(frozen=True)
class UpdateUserDTO:
    first_name: object = UNSET
    last_name: object = UNSET
    username: object = UNSET
    phone: object = UNSET
    role: object = UNSET
    language: object = UNSET
    telegram_id: object = UNSET
    password: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
