from decimal import Decimal, InvalidOperation

from base.interfaces.address import IAddressRepository
from base.exceptions import NotFoundError, ValidationError
from customer.dto.address import CreateAddressDTO, UpdateAddressDTO


class CustomerAddressService:
    def __init__(self, address_repository: IAddressRepository):
        self.address_repo = address_repository

    def list_addresses(self, user_id: int) -> list:
        return list(
            self.address_repo.get_active_by_user(user_id)
            .order_by("-is_default", "-created_at")
        )

    def add_address(self, user_id: int, dto: CreateAddressDTO) -> dict:
        try:
            lat = Decimal(dto.latitude)
            lng = Decimal(dto.longitude)
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid latitude or longitude")

        if not dto.address_text.strip():
            raise ValidationError("address_text is required")

        address = self.address_repo.create(
            user_id=user_id,
            latitude=lat,
            longitude=lng,
            address_text=dto.address_text.strip(),
            label=dto.label,
            entrance=dto.entrance,
            floor=dto.floor,
            apartment=dto.apartment,
            comment=dto.comment,
            is_default=dto.is_default,
        )

        if dto.is_default:
            self.address_repo.set_default(address)

        return {"id": address.id, "address_text": address.address_text}

    def update_address(self, user_id: int, address_id: int, dto: UpdateAddressDTO) -> dict:
        address = self._get_owned_address(user_id, address_id)
        data = dto.to_dict()

        for decimal_field in ("latitude", "longitude"):
            if decimal_field in data:
                try:
                    data[decimal_field] = Decimal(str(data[decimal_field]))
                except (InvalidOperation, ValueError):
                    raise ValidationError(f"Invalid {decimal_field}")

        set_default = data.pop("is_default", None)

        if data:
            self.address_repo.update(address, **data)

        if set_default:
            self.address_repo.set_default(address)

        return {"id": address.id, "address_text": address.address_text}

    def delete_address(self, user_id: int, address_id: int) -> dict:
        address = self._get_owned_address(user_id, address_id)
        self.address_repo.deactivate(address)
        return {"message": "Address deleted"}

    def set_default(self, user_id: int, address_id: int) -> dict:
        address = self._get_owned_address(user_id, address_id)
        self.address_repo.set_default(address)
        return {"message": "Default address updated"}

    def _get_owned_address(self, user_id: int, address_id: int):
        address = (
            self.address_repo.get_all()
            .filter(pk=address_id, user_id=user_id, is_active=True)
            .first()
        )
        if not address:
            raise NotFoundError("Address not found")
        return address
