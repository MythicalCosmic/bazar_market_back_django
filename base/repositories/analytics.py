from typing import Optional
from datetime import date

from django.db.models import QuerySet, Sum, Avg, Count

from base.models import DailyStat, SearchLog
from base.repositories.base import BaseRepository


class DailyStatRepository(BaseRepository[DailyStat]):
    model = DailyStat

    def get_by_date(self, stat_date: date) -> Optional[DailyStat]:
        return self.get_queryset().filter(date=stat_date).first()

    def get_range(self, start: date, end: date) -> QuerySet[DailyStat]:
        return self.get_queryset().filter(date__range=(start, end))

    def upsert(self, stat_date: date, **kwargs) -> tuple[DailyStat, bool]:
        return self.update_or_create(defaults=kwargs, date=stat_date)

    def get_totals_in_range(self, start: date, end: date) -> dict:
        return self.get_range(start, end).aggregate(
            total_orders=Sum("total_orders"),
            total_revenue=Sum("total_revenue"),
            total_users=Sum("total_users"),
            avg_order_value=Avg("avg_order_value"),
        )


class SearchLogRepository(BaseRepository[SearchLog]):
    model = SearchLog

    def log_search(
        self, query: str, results_count: int, user_id: Optional[int] = None
    ) -> SearchLog:
        return self.create(
            query=query,
            results_count=results_count,
            user_id=user_id,
        )

    def get_popular_queries(self, limit: int = 20) -> QuerySet:
        return (
            self.get_queryset()
            .values("query")
            .annotate(search_count=Count("id"))
            .order_by("-search_count")[:limit]
        )

    def get_by_user(self, user_id: int) -> QuerySet[SearchLog]:
        return self.get_queryset().filter(user_id=user_id)

    def get_recent(self, limit: int = 50) -> QuerySet[SearchLog]:
        return self.get_queryset().order_by("-created_at")[:limit]

    def get_zero_result_queries(self, limit: int = 20) -> QuerySet:
        return (
            self.get_queryset()
            .filter(results_count=0)
            .values("query")
            .annotate(search_count=Count("id"))
            .order_by("-search_count")[:limit]
        )
