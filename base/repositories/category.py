from typing import Optional

from django.db.models import QuerySet

from base.models import Category
from base.repositories.base import SoftDeleteRepository


class CategoryRepository(SoftDeleteRepository[Category]):
    model = Category

    def get_by_uuid(self, uuid) -> Optional[Category]:
        return self.get_queryset().filter(uuid=uuid).first()

    def get_root_categories(self) -> QuerySet[Category]:
        return self.get_queryset().filter(parent__isnull=True)

    def get_active_roots(self) -> QuerySet[Category]:
        return self.get_root_categories().filter(is_active=True)

    def get_children(self, parent_id: int) -> QuerySet[Category]:
        return self.get_queryset().filter(parent_id=parent_id)

    def get_active_children(self, parent_id: int) -> QuerySet[Category]:
        return self.get_children(parent_id).filter(is_active=True)

    def get_active(self) -> QuerySet[Category]:
        return self.get_queryset().filter(is_active=True)

    def reorder(self, category_ids: list[int]) -> None:
        for index, pk in enumerate(category_ids):
            self.model.objects.filter(pk=pk).update(sort_order=index)

    def deactivate(self, category: Category) -> Category:
        return self.update(category, is_active=False)

    def activate(self, category: Category) -> Category:
        return self.update(category, is_active=True)
