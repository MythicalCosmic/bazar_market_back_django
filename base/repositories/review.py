from typing import Optional

from django.db.models import QuerySet, Avg

from base.models import Review
from base.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    model = Review

    def get_by_order(self, order_id: int) -> Optional[Review]:
        return self.get_queryset().filter(order_id=order_id).first()

    def get_by_user(self, user_id: int) -> QuerySet[Review]:
        return self.get_queryset().filter(user_id=user_id)

    def has_reviewed(self, user_id: int, order_id: int) -> bool:
        return self.exists(user_id=user_id, order_id=order_id)

    def get_average_rating(self) -> Optional[float]:
        result = self.get_queryset().aggregate(avg=Avg("rating"))
        return result["avg"]

    def get_by_rating(self, rating: int) -> QuerySet[Review]:
        return self.get_queryset().filter(rating=rating)
