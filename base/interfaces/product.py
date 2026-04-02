from abc import abstractmethod
from decimal import Decimal
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import ISoftDeleteRepository
from base.models import Product


class IProductRepository(ISoftDeleteRepository[Product]):

    @abstractmethod
    def get_by_uuid(self, uuid) -> Optional[Product]: ...

    @abstractmethod
    def get_by_category(self, category_id: int) -> QuerySet[Product]: ...

    @abstractmethod
    def get_active(self) -> QuerySet[Product]: ...

    @abstractmethod
    def get_available(self) -> QuerySet[Product]: ...

    @abstractmethod
    def get_available_by_category(self, category_id: int) -> QuerySet[Product]: ...

    @abstractmethod
    def get_featured(self) -> QuerySet[Product]: ...

    @abstractmethod
    def search_by_name(self, query: str) -> QuerySet[Product]: ...

    @abstractmethod
    def search_available_by_name(self, query: str) -> QuerySet[Product]: ...

    @abstractmethod
    def update_stock(self, product: Product, quantity: Decimal) -> Product: ...

    @abstractmethod
    def decrease_stock(self, product_id: int, quantity: Decimal) -> int: ...

    @abstractmethod
    def increase_stock(self, product_id: int, quantity: Decimal) -> int: ...

    @abstractmethod
    def mark_out_of_stock(self, product: Product) -> Product: ...

    @abstractmethod
    def mark_in_stock(self, product: Product) -> Product: ...

    @abstractmethod
    def feature(self, product: Product) -> Product: ...

    @abstractmethod
    def unfeature(self, product: Product) -> Product: ...

    @abstractmethod
    def deactivate(self, product: Product) -> Product: ...

    @abstractmethod
    def activate(self, product: Product) -> Product: ...

    @abstractmethod
    def reorder(self, product_ids: list[int]) -> None: ...

    @abstractmethod
    def get_by_price_range(
        self, min_price: Decimal, max_price: Decimal
    ) -> QuerySet[Product]: ...
