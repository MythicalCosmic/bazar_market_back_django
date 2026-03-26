from typing import Optional

from django.db.models import QuerySet

from base.models import Address
from base.repositories.base import BaseRepository


class AddressRepository(BaseRepository[Address]):
    model = Address

    def get_by_user(self, user_id: int) -> QuerySet[Address]:
        return self.get_queryset().filter(user_id=user_id)

    def get_active_by_user(self, user_id: int) -> QuerySet[Address]:
        return self.get_queryset().filter(user_id=user_id, is_active=True)

    def get_default_for_user(self, user_id: int) -> Optional[Address]:
        return self.get_queryset().filter(
            user_id=user_id, is_default=True, is_active=True
        ).first()

    def set_default(self, address: Address) -> Address:
        self.get_queryset().filter(
            user_id=address.user_id, is_default=True
        ).update(is_default=False)
        address.is_default = True
        address.save(update_fields=["is_default"])
        return address

    def deactivate(self, address: Address) -> Address:
        return self.update(address, is_active=False)

    def activate(self, address: Address) -> Address:
        return self.update(address, is_active=True)
