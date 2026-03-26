from django.db.models import QuerySet

from base.models import Notification
from base.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def get_by_user(self, user_id: int) -> QuerySet[Notification]:
        return self.get_queryset().filter(user_id=user_id)

    def get_unread(self, user_id: int) -> QuerySet[Notification]:
        return self.get_by_user(user_id).filter(is_read=False)

    def get_by_type(self, user_id: int, notification_type: str) -> QuerySet[Notification]:
        return self.get_by_user(user_id).filter(type=notification_type)

    def get_by_channel(self, user_id: int, channel: str) -> QuerySet[Notification]:
        return self.get_by_user(user_id).filter(channel=channel)

    def mark_as_read(self, notification: Notification) -> Notification:
        return self.update(notification, is_read=True)

    def mark_all_as_read(self, user_id: int) -> int:
        return self.get_unread(user_id).update(is_read=True)

    def unread_count(self, user_id: int) -> int:
        return self.get_unread(user_id).count()

    def delete_by_user(self, user_id: int) -> int:
        count, _ = self.get_by_user(user_id).delete()
        return count
