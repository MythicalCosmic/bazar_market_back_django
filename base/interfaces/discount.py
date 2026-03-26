from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import ISoftDeleteRepository
from base.models import Discount


class IDiscountRepository(ISoftDeleteRepository[Discount]):

    @abstractmethod
    def get_by_uuid(self, uuid) -> Optional[Discount]: ...

    @abstractmethod
    def get_active(self) -> QuerySet[Discount]: ...

    @abstractmethod
    def get_current(self) -> QuerySet[Discount]: ...

    @abstractmethod
    def get_for_product(self, product_id: int) -> QuerySet[Discount]: ...

    @abstractmethod
    def get_for_category(self, category_id: int) -> QuerySet[Discount]: ...

    @abstractmethod
    def get_for_product_or_category(
        self, product_id: int, category_id: int
    ) -> QuerySet[Discount]: ...

    @abstractmethod
    def add_products(self, discount: Discount, product_ids: list[int]) -> None: ...

    @abstractmethod
    def remove_products(self, discount: Discount, product_ids: list[int]) -> None: ...

    @abstractmethod
    def set_products(self, discount: Discount, product_ids: list[int]) -> None: ...

    @abstractmethod
    def add_categories(self, discount: Discount, category_ids: list[int]) -> None: ...

    @abstractmethod
    def remove_categories(self, discount: Discount, category_ids: list[int]) -> None: ...

    @abstractmethod
    def set_categories(self, discount: Discount, category_ids: list[int]) -> None: ...

    @abstractmethod
    def deactivate(self, discount: Discount) -> Discount: ...

    @abstractmethod
    def activate(self, discount: Discount) -> Discount: ...
