from base.interfaces.favorite import IFavoriteRepository
from base.interfaces.product import IProductRepository
from base.exceptions import NotFoundError


class CustomerFavoriteService:
    def __init__(
        self,
        favorite_repository: IFavoriteRepository,
        product_repository: IProductRepository,
    ):
        self.fav_repo = favorite_repository
        self.product_repo = product_repository

    def list_favorites(self, user_id: int, page=1, per_page=20):
        qs = self.fav_repo.get_by_user(user_id).select_related("product", "product__category")
        return self.fav_repo.paginate(qs, page, per_page)

    def toggle(self, user_id: int, product_id: int) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise NotFoundError("Product not found")

        is_favorited, _ = self.fav_repo.toggle(user_id, product_id)
        return {"product_id": product_id, "is_favorited": is_favorited}

    def is_favorited(self, user_id: int, product_id: int) -> bool:
        return self.fav_repo.is_favorited(user_id, product_id)

    def get_favorite_product_ids(self, user_id: int) -> list[int]:
        return list(self.fav_repo.get_user_product_ids(user_id))
