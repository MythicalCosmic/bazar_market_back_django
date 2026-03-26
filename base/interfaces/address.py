from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import Address


class IAddressRepository(IBaseRepository[Address]):

    @abstractmethod
    def get_by_user(self, user_id: int) -> QuerySet[Address]: ...

    @abstractmethod
    def get_active_by_user(self, user_id: int) -> QuerySet[Address]: ...

    @abstractmethod
    def get_default_for_user(self, user_id: int) -> Optional[Address]: ...

    @abstractmethod
    def set_default(self, address: Address) -> Address: ...

    @abstractmethod
    def deactivate(self, address: Address) -> Address: ...

    @abstractmethod
    def activate(self, address: Address) -> Address: ...
