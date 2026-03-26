from typing import Optional

from django.db.models import QuerySet
from django.utils import timezone

from base.models import User
from base.repositories.base import SoftDeleteRepository


class UserRepository(SoftDeleteRepository[User]):
    model = User

    def get_by_uuid(self, uuid) -> Optional[User]:
        return self.get_queryset().filter(uuid=uuid).first()

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        return self.get_queryset().filter(telegram_id=telegram_id).first()

    def get_by_phone(self, phone: str) -> Optional[User]:
        return self.get_queryset().filter(phone=phone).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.get_queryset().filter(username=username).first()

    def get_by_role(self, role: str) -> QuerySet[User]:
        return self.get_queryset().filter(role=role)

    def get_active(self) -> QuerySet[User]:
        return self.get_queryset().filter(is_active=True)

    def get_clients(self) -> QuerySet[User]:
        return self.get_by_role(User.Role.CLIENT)

    def get_couriers(self) -> QuerySet[User]:
        return self.get_by_role(User.Role.COURIER)

    def get_managers(self) -> QuerySet[User]:
        return self.get_by_role(User.Role.MANAGER)

    def get_admins(self) -> QuerySet[User]:
        return self.get_by_role(User.Role.ADMIN)

    def update_last_seen(self, user: User) -> User:
        user.last_seen_at = timezone.now()
        user.save(update_fields=["last_seen_at"])
        return user

    def deactivate(self, user: User) -> User:
        return self.update(user, is_active=False)

    def activate(self, user: User) -> User:
        return self.update(user, is_active=True)

    def set_language(self, user: User, language: str) -> User:
        return self.update(user, language=language)
