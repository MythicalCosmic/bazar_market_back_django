from base.interfaces.notification import INotificationRepository
from base.exceptions import NotFoundError


class CustomerNotificationService:
    def __init__(self, notification_repository: INotificationRepository):
        self.notif_repo = notification_repository

    def list_notifications(self, user_id: int, page=1, per_page=20):
        qs = self.notif_repo.get_by_user(user_id)
        return self.notif_repo.paginate(qs, page, per_page)

    def mark_as_read(self, user_id: int, notification_id: int) -> dict:
        notif = self.notif_repo.get_all().filter(pk=notification_id, user_id=user_id).first()
        if not notif:
            raise NotFoundError("Notification not found")
        self.notif_repo.mark_as_read(notif)
        return {"message": "Marked as read"}

    def mark_all_as_read(self, user_id: int) -> dict:
        count = self.notif_repo.mark_all_as_read(user_id)
        return {"message": f"{count} notifications marked as read"}

    def unread_count(self, user_id: int) -> int:
        return self.notif_repo.unread_count(user_id)
