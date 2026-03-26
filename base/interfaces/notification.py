from abc import abstractmethod

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import Notification


class INotificationRepository(IBaseRepository[Notification]):

    @abstractmethod
    def get_by_user(self, user_id: int) -> QuerySet[Notification]: ...

    @abstractmethod
    def get_unread(self, user_id: int) -> QuerySet[Notification]: ...

    @abstractmethod
    def get_by_type(
        self, user_id: int, notification_type: str
    ) -> QuerySet[Notification]: ...

    @abstractmethod
    def get_by_channel(
        self, user_id: int, channel: str
    ) -> QuerySet[Notification]: ...

    @abstractmethod
    def mark_as_read(self, notification: Notification) -> Notification: ...

    @abstractmethod
    def mark_all_as_read(self, user_id: int) -> int: ...

    @abstractmethod
    def unread_count(self, user_id: int) -> int: ...

    @abstractmethod
    def delete_by_user(self, user_id: int) -> int: ...
