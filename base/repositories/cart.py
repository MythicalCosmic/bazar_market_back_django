from typing import Optional
from decimal import Decimal

from django.db.models import QuerySet

from base.models import CartItem
from base.repositories.base import BaseRepository


class CartItemRepository(BaseRepository[CartItem]):
    model = CartItem

    def get_by_user(self, user_id: int) -> QuerySet[CartItem]:
        return self.get_queryset().filter(user_id=user_id).select_related("product")

    def get_by_user_and_product(
        self, user_id: int, product_id: int
    ) -> Optional[CartItem]:
        return self.get_queryset().filter(
            user_id=user_id, product_id=product_id
        ).first()

    def add_item(self, user_id: int, product_id: int, quantity: Decimal) -> CartItem:
        item, _ = self.model.objects.update_or_create(
            user_id=user_id,
            product_id=product_id,
            defaults={"quantity": quantity},
        )
        return item

    def update_quantity(self, item: CartItem, quantity: Decimal) -> CartItem:
        return self.update(item, quantity=quantity)

    def remove_item(self, user_id: int, product_id: int) -> int:
        count, _ = self.get_queryset().filter(
            user_id=user_id, product_id=product_id
        ).delete()
        return count

    def clear_cart(self, user_id: int) -> int:
        count, _ = self.get_queryset().filter(user_id=user_id).delete()
        return count

    def cart_count(self, user_id: int) -> int:
        return self.get_queryset().filter(user_id=user_id).count()
