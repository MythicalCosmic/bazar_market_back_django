from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import ISoftDeleteRepository
from base.models import Category


class ICategoryRepository(ISoftDeleteRepository[Category]):

    @abstractmethod
    def get_by_uuid(self, uuid) -> Optional[Category]: ...

    @abstractmethod
    def get_root_categories(self) -> QuerySet[Category]: ...

    @abstractmethod
    def get_active_roots(self) -> QuerySet[Category]: ...

    @abstractmethod
    def get_children(self, parent_id: int) -> QuerySet[Category]: ...

    @abstractmethod
    def get_active_children(self, parent_id: int) -> QuerySet[Category]: ...

    @abstractmethod
    def get_active(self) -> QuerySet[Category]: ...

    @abstractmethod
    def reorder(self, category_ids: list[int]) -> None: ...

    @abstractmethod
    def deactivate(self, category: Category) -> Category: ...

    @abstractmethod
    def activate(self, category: Category) -> Category: ...
