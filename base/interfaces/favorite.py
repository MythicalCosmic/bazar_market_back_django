from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import Favorite


class IFavoriteRepository(IBaseRepository[Favorite]):

    @abstractmethod
    def get_by_user(self, user_id: int) -> QuerySet[Favorite]: ...

    @abstractmethod
    def is_favorited(self, user_id: int, product_id: int) -> bool: ...

    @abstractmethod
    def toggle(
        self, user_id: int, product_id: int
    ) -> tuple[bool, Optional[Favorite]]: ...

    @abstractmethod
    def add(self, user_id: int, product_id: int) -> Favorite: ...

    @abstractmethod
    def remove(self, user_id: int, product_id: int) -> int: ...

    @abstractmethod
    def get_user_product_ids(self, user_id: int) -> list[int]: ...
