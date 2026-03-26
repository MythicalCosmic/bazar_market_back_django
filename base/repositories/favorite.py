from typing import Optional

from django.db.models import QuerySet

from base.models import Favorite
from base.repositories.base import BaseRepository


class FavoriteRepository(BaseRepository[Favorite]):
    model = Favorite

    def get_by_user(self, user_id: int) -> QuerySet[Favorite]:
        return self.get_queryset().filter(user_id=user_id).select_related("product")

    def is_favorited(self, user_id: int, product_id: int) -> bool:
        return self.exists(user_id=user_id, product_id=product_id)

    def toggle(self, user_id: int, product_id: int) -> tuple[bool, Optional[Favorite]]:
        try:
            favorite = self.get_queryset().get(
                user_id=user_id, product_id=product_id
            )
            favorite.delete()
            return False, None
        except self.model.DoesNotExist:
            favorite = self.create(user_id=user_id, product_id=product_id)
            return True, favorite

    def add(self, user_id: int, product_id: int) -> Favorite:
        favorite, _ = self.get_or_create(user_id=user_id, product_id=product_id)
        return favorite

    def remove(self, user_id: int, product_id: int) -> int:
        count, _ = self.get_queryset().filter(
            user_id=user_id, product_id=product_id
        ).delete()
        return count

    def get_user_product_ids(self, user_id: int) -> list[int]:
        return list(
            self.get_queryset()
            .filter(user_id=user_id)
            .values_list("product_id", flat=True)
        )
