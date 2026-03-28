from abc import abstractmethod
from typing import Optional

from base.interfaces.base import IBaseRepository
from base.models import Session, User


class ISessionRepository(IBaseRepository[Session]):

    @abstractmethod
    def create_session(
        self, user: User, ip: str, ua: str, device: str, hours: int = 72
    ) -> Session: ...

    @abstractmethod
    def get_by_key(self, key: str) -> Optional[Session]: ...

    @abstractmethod
    def invalidate(self, session: Session) -> None: ...

    @abstractmethod
    def invalidate_all_for_user(self, user: User) -> None: ...

    @abstractmethod
    def clear_expired(self) -> int: ...
