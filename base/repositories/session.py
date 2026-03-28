import hashlib
import uuid
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from base.models import Session, User
from base.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    model = Session

    def _generate_key(self) -> str:
        raw = f"{uuid.uuid4()}{timezone.now().isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def create_session(
        self, user: User, ip: str, ua: str, device: str, hours: int = 72
    ) -> Session:
        Session.objects.filter(expires_at__lt=timezone.now()).delete()
        return Session.objects.create(
            key=self._generate_key(),
            user=user,
            ip_address=ip,
            user_agent=ua,
            device=device,
            expires_at=timezone.now() + timedelta(hours=hours),
        )

    def get_by_key(self, key: str) -> Optional[Session]:
        try:
            session = Session.objects.select_related("user").get(
                key=key, is_active=True, expires_at__gt=timezone.now()
            )
            session.save(update_fields=["last_activity_at"])
            return session
        except Session.DoesNotExist:
            return None

    def invalidate(self, session: Session) -> None:
        session.is_active = False
        session.save(update_fields=["is_active"])

    def invalidate_all_for_user(self, user: User) -> None:
        Session.objects.filter(user=user, is_active=True).update(is_active=False)

    def clear_expired(self) -> int:
        count, _ = Session.objects.filter(expires_at__lt=timezone.now()).delete()
        return count
