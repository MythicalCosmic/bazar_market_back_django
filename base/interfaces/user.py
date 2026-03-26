from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import ISoftDeleteRepository
from base.models import User


class IUserRepository(ISoftDeleteRepository[User]):

    @abstractmethod
    def get_by_uuid(self, uuid) -> Optional[User]: ...

    @abstractmethod
    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]: ...

    @abstractmethod
    def get_by_phone(self, phone: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_role(self, role: str) -> QuerySet[User]: ...

    @abstractmethod
    def get_active(self) -> QuerySet[User]: ...

    @abstractmethod
    def get_clients(self) -> QuerySet[User]: ...

    @abstractmethod
    def get_couriers(self) -> QuerySet[User]: ...

    @abstractmethod
    def get_managers(self) -> QuerySet[User]: ...

    @abstractmethod
    def get_admins(self) -> QuerySet[User]: ...

    @abstractmethod
    def update_last_seen(self, user: User) -> User: ...

    @abstractmethod
    def deactivate(self, user: User) -> User: ...

    @abstractmethod
    def activate(self, user: User) -> User: ...

    @abstractmethod
    def set_language(self, user: User, language: str) -> User: ...
