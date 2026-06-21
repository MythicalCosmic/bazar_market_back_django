"""Courier auth — username + password, restricted to role=courier.

Reuses the shared session system (opaque `session.key` as the Bearer token, the
same one `base.permissions.require_auth`/`require_role` validate). Presented in
the app's accessToken/refreshToken/expiresIn shape; refresh ROTATES the session
(old key invalidated, new key issued).
"""
from django.utils import timezone

from base.interfaces.user import IUserRepository
from base.interfaces.session import ISessionRepository
from base.exceptions import AuthenticationError, ForbiddenError
from base.models import User

from courier.dto.auth import LoginDTO, SessionDTO
from courier.models import CourierProfile
from courier.serializers import courier_public


class CourierAuthService:
    def __init__(self, user_repo: IUserRepository, session_repo: ISessionRepository):
        self._users = user_repo
        self._sessions = session_repo

    def _tokens(self, session) -> dict:
        expires_in = max(0, int((session.expires_at - timezone.now()).total_seconds()))
        return {
            "accessToken": session.key,
            "refreshToken": session.key,
            "expiresIn": expires_in,
        }

    def _require_courier(self, user):
        if not user or user.role != User.Role.COURIER:
            raise ForbiddenError("Not a courier account")
        if not user.is_active:
            raise ForbiddenError("Account is disabled")

    def login(self, credentials: LoginDTO, session_info: SessionDTO) -> dict:
        user = self._users.get_by_username(credentials.username)
        # Constant-ish behaviour: same error whether the user is missing or the
        # password is wrong (don't leak which usernames exist).
        if not user or not user.check_password(credentials.password):
            raise AuthenticationError("invalid_credentials")
        self._require_courier(user)
        self._users.update_last_seen(user)
        profile, _ = CourierProfile.objects.get_or_create(user=user)
        session = self._sessions.create_session(
            user, session_info.ip_address, session_info.user_agent, session_info.device
        )
        return {**self._tokens(session), "courier": courier_public(user, profile)}

    def refresh(self, refresh_token: str, session_info: SessionDTO) -> dict:
        session = self._sessions.get_by_key(refresh_token)
        if not session:
            raise AuthenticationError("invalid_refresh_token")
        user = session.user
        self._require_courier(user)
        # Rotate: kill the old session, issue a fresh one.
        self._sessions.invalidate(session)
        new_session = self._sessions.create_session(
            user, session_info.ip_address, session_info.user_agent, session_info.device
        )
        profile = CourierProfile.objects.filter(user=user).first()
        return {**self._tokens(new_session), "courier": courier_public(user, profile)}

    def logout(self, token: str) -> dict:
        session = self._sessions.get_by_key(token)
        if session:
            self._sessions.invalidate(session)
        return {"message": "Logged out"}
