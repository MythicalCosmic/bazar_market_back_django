from abc import abstractmethod
from datetime import date
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import DailyStat, SearchLog


class IDailyStatRepository(IBaseRepository[DailyStat]):

    @abstractmethod
    def get_by_date(self, stat_date: date) -> Optional[DailyStat]: ...

    @abstractmethod
    def get_range(self, start: date, end: date) -> QuerySet[DailyStat]: ...

    @abstractmethod
    def upsert(self, stat_date: date, **kwargs) -> tuple[DailyStat, bool]: ...

    @abstractmethod
    def get_totals_in_range(self, start: date, end: date) -> dict: ...


class ISearchLogRepository(IBaseRepository[SearchLog]):

    @abstractmethod
    def log_search(
        self, query: str, results_count: int, user_id: Optional[int] = None
    ) -> SearchLog: ...

    @abstractmethod
    def get_popular_queries(self, limit: int = 20) -> QuerySet: ...

    @abstractmethod
    def get_by_user(self, user_id: int) -> QuerySet[SearchLog]: ...

    @abstractmethod
    def get_recent(self, limit: int = 50) -> QuerySet[SearchLog]: ...

    @abstractmethod
    def get_zero_result_queries(self, limit: int = 20) -> QuerySet: ...
