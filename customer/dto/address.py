from dataclasses import dataclass, fields


UNSET = object()


@dataclass(frozen=True)
class CreateAddressDTO:
    latitude: str
    longitude: str
    address_text: str
    label: str = ""
    entrance: str = ""
    floor: str = ""
    apartment: str = ""
    comment: str = ""
    is_default: bool = False


@dataclass(frozen=True)
class UpdateAddressDTO:
    latitude: object = UNSET
    longitude: object = UNSET
    address_text: object = UNSET
    label: object = UNSET
    entrance: object = UNSET
    floor: object = UNSET
    apartment: object = UNSET
    comment: object = UNSET
    is_default: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
