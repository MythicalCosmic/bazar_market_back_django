from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import ProductImage


class IProductImageRepository(IBaseRepository[ProductImage]):

    @abstractmethod
    def get_by_product(self, product_id: int) -> QuerySet[ProductImage]: ...

    @abstractmethod
    def get_primary(self, product_id: int) -> Optional[ProductImage]: ...

    @abstractmethod
    def set_primary(self, image: ProductImage) -> ProductImage: ...

    @abstractmethod
    def reorder(self, image_ids: list[int]) -> None: ...

    @abstractmethod
    def delete_by_product(self, product_id: int) -> int: ...
