from abc import abstractmethod
from typing import Optional, Any

from base.interfaces.base import IBaseRepository
from base.models import Setting


class ISettingRepository(IBaseRepository[Setting]):

    @abstractmethod
    def get_by_key(self, key: str) -> Optional[Setting]: ...

    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any: ...

    @abstractmethod
    def set_value(
        self,
        key: str,
        value: Any,
        value_type: str = Setting.ValueType.STRING,
        description: str = "",
    ) -> Setting: ...

    @abstractmethod
    def get_all_as_dict(self) -> dict[str, Any]: ...

    @abstractmethod
    def delete_by_key(self, key: str) -> int: ...
