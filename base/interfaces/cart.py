from abc import abstractmethod
from decimal import Decimal
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import CartItem


class ICartItemRepository(IBaseRepository[CartItem]):

    @abstractmethod
    def get_by_user(self, user_id: int) -> QuerySet[CartItem]: ...

    @abstractmethod
    def get_by_user_and_product(
        self, user_id: int, product_id: int
    ) -> Optional[CartItem]: ...

    @abstractmethod
    def add_item(
        self, user_id: int, product_id: int, quantity: Decimal
    ) -> CartItem: ...

    @abstractmethod
    def update_quantity(self, item: CartItem, quantity: Decimal) -> CartItem: ...

    @abstractmethod
    def remove_item(self, user_id: int, product_id: int) -> int: ...

    @abstractmethod
    def clear_cart(self, user_id: int) -> int: ...

    @abstractmethod
    def cart_count(self, user_id: int) -> int: ...
