from django.db import transaction
from django.db.models import Count, Sum, Q

from base.interfaces.category import ICategoryRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.category import CreateCategoryDTO, UpdateCategoryDTO
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
        qs = self.category_repository.apply_ordering(qs, order_by, {"sort_order", "name_uz", "created_at"})
        return self.category_repository.paginate(qs, page, per_page)

    def get_by_id(self, category_id: int) -> Category | None:
        return self.category_repository.get_by_id(category_id)

    def get_tree(self):
        roots = list(
            self.category_repository.get_all()
            .filter(parent__isnull=True)
            .order_by("sort_order")
            .annotate(children_count=Count("children", filter=Q(children__deleted_at__isnull=True)))
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

    def create_category(self, dto: CreateCategoryDTO) -> dict:
        if dto.parent_id:
            parent = self.category_repository.get_by_id(dto.parent_id)
            if not parent:
                raise ValidationError("Parent category not found")
            if parent.parent_id is not None:
                raise ValidationError("Only one level of nesting allowed")

        category = self.category_repository.create(
            name_uz=dto.name_uz,
            name_ru=dto.name_ru,
            image=dto.image,
            parent_id=dto.parent_id,
            sort_order=dto.sort_order,
            is_active=dto.is_active,
        )
        return {"id": category.id, "name_uz": category.name_uz}

    def update_category(self, category_id: int, dto: UpdateCategoryDTO) -> dict:
        category = self.category_repository.get_by_id(category_id)
        if not category:
            raise NotFoundError("Category not found")

        data = dto.to_dict()

        if "parent_id" in data:
            new_parent_id = data["parent_id"]
            if new_parent_id == category_id:
                raise ValidationError("Category cannot be its own parent")
            if new_parent_id is not None:
                parent = self.category_repository.get_by_id(new_parent_id)
                if not parent:
                    raise ValidationError("Parent category not found")
                if parent.parent_id is not None:
                    raise ValidationError("Only one level of nesting allowed")
            child_ids = list(
                self.category_repository.get_all()
                .filter(parent_id=category_id)
                .values_list("id", flat=True)
            )
            if new_parent_id in child_ids:
                raise ValidationError("Cannot set child as parent")

        if data:
            self.category_repository.update(category, **data)

        return {"id": category.id, "name_uz": category.name_uz}

    def delete_category(self, category_id: int) -> dict:
        category = self.category_repository.get_by_id(category_id)
        if not category:
            raise NotFoundError("Category not found")

        has_children = self.category_repository.get_all().filter(parent_id=category_id).exists()
        if has_children:
            raise ValidationError("Cannot delete category with subcategories. Delete children first.")

        has_products = category.products.filter(deleted_at__isnull=True).exists()
        if has_products:
            raise ValidationError("Cannot delete category with active products. Move or delete products first.")

        self.category_repository.soft_delete(category)
        return {"message": "Category deleted"}

    def restore_category(self, category_id: int) -> dict:
        category = self.category_repository.get_only_deleted().filter(pk=category_id).first()
        if not category:
            raise NotFoundError("Category not found or not deleted")

        if category.parent_id:
            parent = self.category_repository.get_by_id(category.parent_id)
            if not parent:
                raise ValidationError("Parent category no longer exists. Update parent before restoring.")

        self.category_repository.restore(category)
        return {"message": "Category restored"}

    @transaction.atomic
    def reorder(self, category_ids: list[int]) -> dict:
        existing = set(
            self.category_repository.get_all()
            .filter(pk__in=category_ids)
            .values_list("pk", flat=True)
        )
        missing = set(category_ids) - existing
        if missing:
            raise ValidationError(f"Categories not found: {missing}")

        self.category_repository.reorder(category_ids)
        return {"message": "Categories reordered"}

    def activate(self, category_id: int) -> dict:
        category = self.category_repository.get_by_id(category_id)
        if not category:
            raise NotFoundError("Category not found")
        self.category_repository.activate(category)
        return {"message": "Category activated"}

    def deactivate(self, category_id: int) -> dict:
        category = self.category_repository.get_by_id(category_id)
        if not category:
            raise NotFoundError("Category not found")
        self.category_repository.deactivate(category)
        return {"message": "Category deactivated"}

    def stats(self, date_from=None, date_to=None) -> dict:
        qs = self.category_repository.get_all()

        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        total = qs.count()
        active = qs.filter(is_active=True).count()
        roots = qs.filter(parent__isnull=True).count()

        all_cats = self.category_repository.get_all()
        product_stats = list(
            all_cats.annotate(
                product_count=Count("products", filter=Q(products__deleted_at__isnull=True, products__is_active=True))
            )
            .filter(product_count__gt=0)
            .order_by("-product_count")
            .values("id", "name_uz", "product_count")[:10]
        )

        order_filter = Q(products__order_items__order__status__in=["completed", "delivered"])
        if date_from:
            order_filter &= Q(products__order_items__order__created_at__gte=date_from)
        if date_to:
            order_filter &= Q(products__order_items__order__created_at__lte=date_to)

        revenue_stats = list(
            all_cats.annotate(
                revenue=Sum("products__order_items__total", filter=order_filter),
                order_count=Count("products__order_items__order", filter=order_filter, distinct=True),
            )
            .filter(revenue__isnull=False)
            .order_by("-revenue")
            .values("id", "name_uz", "revenue", "order_count")[:10]
        )

        empty = all_cats.annotate(
            product_count=Count("products", filter=Q(products__deleted_at__isnull=True))
        ).filter(product_count=0).count()

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "root_categories": roots,
            "subcategories": total - roots,
            "empty_categories": empty,
            "top_by_products": [
                {"id": s["id"], "name": s["name_uz"], "product_count": s["product_count"]}
                for s in product_stats
            ],
            "top_by_revenue": [
                {
                    "id": s["id"],
                    "name": s["name_uz"],
                    "revenue": str(s["revenue"] or 0),
                    "order_count": s["order_count"],
                }
                for s in revenue_stats
            ],
        }
