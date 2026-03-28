import hashlib
import uuid
from datetime import timedelta
from typing import Optional

from django.core.cache import cache
from django.utils import timezone

from base.models import Session, User
from base.repositories.base import BaseRepository

SESSION_PREFIX = "session:"
ACTIVITY_THRESHOLD = 300


class SessionRepository(BaseRepository[Session]):
    model = Session

    def _generate_key(self) -> str:
        raw = f"{uuid.uuid4()}{timezone.now().isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cache_key(self, key: str) -> str:
        return f"{SESSION_PREFIX}{key}"

    def create_session(
        self, user: User, ip: str, ua: str, device: str, hours: int = 72
    ) -> Session:
        Session.objects.filter(expires_at__lt=timezone.now()).delete()
        session = Session.objects.create(
            key=self._generate_key(),
            user=user,
            ip_address=ip,
            user_agent=ua,
            device=device,
            expires_at=timezone.now() + timedelta(hours=hours),
        )
        ttl = int((session.expires_at - timezone.now()).total_seconds())
        cache.set(self._cache_key(session.key), True, ttl)
        return session

    def get_by_key(self, key: str) -> Optional[Session]:
        cached = cache.get(self._cache_key(key))

        if cached is True:
            try:
                session = Session.objects.select_related("user").get(
                    pk=key, is_active=True
                )
                self._touch_activity(session)
                return session
            except Session.DoesNotExist:
                cache.delete(self._cache_key(key))
                return None

        try:
            session = Session.objects.select_related("user").get(
                key=key, is_active=True, expires_at__gt=timezone.now()
            )
            ttl = int((session.expires_at - timezone.now()).total_seconds())
            cache.set(self._cache_key(session.key), True, ttl)
            self._touch_activity(session)
            return session
        except Session.DoesNotExist:
            return None

    def _touch_activity(self, session: Session) -> None:
        if session.last_activity_at:
            delta = (timezone.now() - session.last_activity_at).total_seconds()
            if delta < ACTIVITY_THRESHOLD:
                return
        session.save(update_fields=["last_activity_at"])

    def invalidate(self, session: Session) -> None:
        cache.delete(self._cache_key(session.key))
        session.is_active = False
        session.save(update_fields=["is_active"])

    def invalidate_all_for_user(self, user: User) -> None:
        keys = list(
            Session.objects.filter(user=user, is_active=True)
            .values_list("key", flat=True)
        )
        for key in keys:
            cache.delete(self._cache_key(key))
        Session.objects.filter(user=user, is_active=True).update(is_active=False)

    def clear_expired(self) -> int:
        count, _ = Session.objects.filter(expires_at__lt=timezone.now()).delete()
        return count
