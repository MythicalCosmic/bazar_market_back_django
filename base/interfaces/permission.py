from abc import abstractmethod

from base.interfaces.base import IBaseRepository


class IPermissionRepository(IBaseRepository):
    @abstractmethod
    def get_by_codename(self, codename: str): ...

    @abstractmethod
    def get_by_group(self, group: str): ...

    @abstractmethod
    def get_all_codenames(self) -> set: ...


class IRolePermissionRepository(IBaseRepository):
    @abstractmethod
    def get_for_role(self, role: str) -> list: ...

    @abstractmethod
    def get_codenames_for_role(self, role: str) -> set: ...

    @abstractmethod
    def assign(self, role: str, permission) -> object: ...

    @abstractmethod
    def revoke(self, role: str, permission) -> bool: ...

    @abstractmethod
    def sync_role(self, role: str, codenames: set) -> None: ...


class IUserPermissionRepository(IBaseRepository):
    @abstractmethod
    def get_for_user(self, user_id: int) -> list: ...

    @abstractmethod
    def grant(self, user_id: int, permission) -> object: ...

    @abstractmethod
    def deny(self, user_id: int, permission) -> object: ...

    @abstractmethod
    def remove(self, user_id: int, permission) -> bool: ...

    @abstractmethod
    def clear_for_user(self, user_id: int) -> int: ...
