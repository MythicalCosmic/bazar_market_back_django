from base.interfaces.user import IUserRepository
from base.interfaces.session import ISessionRepository
from base.exceptions import NotFoundError, AuthenticationError
from admins.dto.auth import LoginDTO, SessionDTO


class AuthService:

    def __init__(self, user_repo: IUserRepository, session_repo: ISessionRepository):
        self._users = user_repo
        self._sessions = session_repo

    def login(self, credentials: LoginDTO, session_info: SessionDTO) -> dict:
        user = self._users.get_by_username(credentials.username)
        if not user:
            raise NotFoundError("User not found")
        if not user.check_password(credentials.password):
            raise AuthenticationError("Invalid credentials")
        self._users.update_last_seen(user)
        session = self._sessions.create_session(
            user=user,
            ip=session_info.ip_address,
            ua=session_info.user_agent,
            device=session_info.device,
        )
        return {
            "session_key": session.key,
            "user": {
                "id": user.id,
                "uuid": str(user.uuid),
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
            },
            "expires_at": session.expires_at.isoformat(),
        }
    

    def logout(self, session_token: str) -> dict:
        session = self._sessions.get_by_key(session_token)
        if not session:
            raise AuthenticationError("Invalid or expired session")
        self._sessions.invalidate(session)
        return {"message": "Logged out"}
    
    def logout_all(self, session_token: str) -> dict:
        session = self._sessions.get_by_key(session_token)

        if not session:
            raise AuthenticationError("Invalid or expired session")
        self._sessions.invalidate_all_for_user(session.user)

        return {"message": "Logged out"}
    
    def me(self, session_token: str) -> dict:
        session = self._sessions.get_by_key(session_token)

        if not session:
            raise AuthenticationError("Invalid or expired session")
    
        user = session.user

        return {
            "id": user.id,
            "username": user.username,
            "full_name": user.first_name + " " + user.last_name,
            "role": user.role,
        }