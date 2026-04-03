from django.db.models import Count

from base.interfaces.favorite import IFavoriteRepository
from base.models import Favorite


class FavoriteService:
    def __init__(self, favorite_repository: IFavoriteRepository):
        self.fav_repo = favorite_repository

    def get_all(
        self,
        user_id=None,
        product_id=None,
        order_by="-created_at",
        page=1,
        per_page=20,
    ):
        qs = self.fav_repo.get_all().select_related("user", "product")

        if user_id is not None:
            qs = qs.filter(user_id=user_id)
        if product_id is not None:
            qs = qs.filter(product_id=product_id)

        qs = self.fav_repo.apply_ordering(qs, order_by, {"created_at"})
        return self.fav_repo.paginate(qs, page, per_page)

    def most_favorited(self, limit: int = 20) -> list[dict]:
        from base.models import Product
        qs = (
            Favorite.objects
            .values("product_id", "product__name_uz", "product__price")
            .annotate(favorite_count=Count("id"))
            .order_by("-favorite_count")[:limit]
        )
        return [
            {
                "product_id": row["product_id"],
                "name": row["product__name_uz"],
                "price": str(row["product__price"]),
                "favorite_count": row["favorite_count"],
            }
            for row in qs
        ]

    def stats(self) -> dict:
        total = self.fav_repo.get_all().count()
        unique_users = self.fav_repo.get_all().values("user_id").distinct().count()
        unique_products = self.fav_repo.get_all().values("product_id").distinct().count()

        return {
            "total_favorites": total,
            "unique_users": unique_users,
            "unique_products": unique_products,
            "avg_per_user": round(total / unique_users, 1) if unique_users else 0,
            "most_favorited": self.most_favorited(10),
        }
