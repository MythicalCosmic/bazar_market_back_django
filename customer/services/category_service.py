from django.db.models import Count, Sum, Q
from base.interfaces.category import ICategoryRepository
from base.exceptions import NotFoundError
from base.models import Category


class CategoryService:
    def __init__(self, category_repository: ICategoryRepository):
        self.category_repository = category_repository

    
    def get_all(self, query=None, is_active=None, parent_id=None, order_by="sort_order", page=1, per_page=20, is_deleted=None):
        if is_deleted:
            qs = self.category_repository.get_only_deleted()
            return self.category_repository.paginate(qs, page, per_page)
        qs = self.category_repository.get_all()
        qs = self.category_repository.search(qs, query, ["name_uz", "name_ru"])
        filters = {"is_active": is_active}
        if parent_id == 0:
            filters["parent_id__isnull"] = True
        elif parent_id is not None:
            filters["parent_id"] = parent_id
            qs = self.category_repository.apply_filters(qs, filters)
            qs = self.category_repository.apply_ordering(qs, order_by, "sort_order", "name_uz", "created_at")
            return self.category_repository.paginate(qs, page, per_page)
        
    def get_by_id(self, category_id: int) -> Category | None:
        return self.category_repository.get_by_id(category_id)
    
    def get_tree(self):
        roots = list(
            self.category_repository.get_all().filter(parent_isnull=True).order_by("sort_order").annotate(children_count=Count("childer", filter=Q(children_deleted_at__isnull=True)))
        )
        root_ids = [r.id for r in roots]
        children = list(
            self.category_repository.get_all()
            .filter(parent_id__in=root_ids)
            .order_by("sort_order")
        )
        children_map = {}
        for c in children:
            children_map.setdefault(c.parent_id, []).append(c)

        return [
            {
                "id": r.id,
                "name_uz": r.name_uz,
                "name_ru": r.name_ru,
                "image": r.image,
                "sort_order": r.sort_order,
                "is_active": r.is_active,
                "children_count": r.children_count,
                "children": [
                    {
                        "id": ch.id,
                        "name_uz": ch.name_uz,
                        "name_ru": ch.name_ru,
                        "image": ch.image,
                        "sort_order": ch.sort_order,
                        "is_active": ch.is_active,
                    }
                    for ch in children_map.get(r.id, [])
                ],
            }
            for r in roots
        ]