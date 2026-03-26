from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import Review


class IReviewRepository(IBaseRepository[Review]):

    @abstractmethod
    def get_by_order(self, order_id: int) -> Optional[Review]: ...

    @abstractmethod
    def get_by_user(self, user_id: int) -> QuerySet[Review]: ...

    @abstractmethod
    def has_reviewed(self, user_id: int, order_id: int) -> bool: ...

    @abstractmethod
    def get_average_rating(self) -> Optional[float]: ...

    @abstractmethod
    def get_by_rating(self, rating: int) -> QuerySet[Review]: ...
