from decimal import Decimal

from django.db.models import Q, Subquery, OuterRef, Sum, Count
from django.utils import timezone

from base.interfaces.product import IProductRepository
from base.interfaces.category import ICategoryRepository
from base.interfaces.discount import IDiscountRepository
from base.models import ProductImage, Discount, OrderItem


class CatalogService:
    def __init__(
        self,
        product_repository: IProductRepository,
        category_repository: ICategoryRepository,
        discount_repository: IDiscountRepository,
    ):
        self.product_repo = product_repository
        self.category_repo = category_repository
        self.discount_repo = discount_repository

    def list_products(
        self,
        category_id=None,
        query=None,
        is_featured=None,
        order_by="sort_order",
        page=1,
        per_page=20,
    ):
        qs = self.product_repo.get_all().filter(is_active=True).select_related("category")

        if category_id is not None:
            qs = qs.filter(category_id=category_id)

        if query:
            qs = self.product_repo.search(qs, query, ["name_uz", "name_ru", "description_uz", "description_ru"])

        if is_featured is not None:
            qs = qs.filter(is_featured=is_featured)

        primary_img = Subquery(
            ProductImage.objects.filter(
                product=OuterRef("pk"), is_primary=True
            ).values("image")[:1]
        )
        qs = qs.annotate(primary_image=primary_img)

        qs = self.product_repo.apply_ordering(qs, order_by, {"sort_order", "price", "name_uz", "created_at"})

        result = self.product_repo.paginate(qs, page, per_page)
        self._attach_discounts(result["items"])
        return result

    def get_product(self, product_id: int):
        product = (
            self.product_repo.get_all()
            .filter(pk=product_id, is_active=True)
            .select_related("category")
            .prefetch_related("images")
            .first()
        )
        if not product:
            return None

        now = timezone.now()
        discounts = list(
            Discount.objects.filter(
                Q(products=product.pk) | Q(categories=product.category_id),
                is_active=True,
                deleted_at__isnull=True,
            ).filter(
                Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                Q(expires_at__isnull=True) | Q(expires_at__gte=now),
            ).distinct().values("id", "name_uz", "type", "value", "max_discount")
        )
        product._current_discounts = discounts
        return product

    def list_categories(self):
        return list(
            self.category_repo.get_all()
            .filter(is_active=True)
            .annotate(product_count=Count(
                "products",
                filter=Q(products__is_active=True, products__deleted_at__isnull=True),
            ))
            .order_by("sort_order")
        )

    def get_category_tree(self):
        roots = list(
            self.category_repo.get_all()
            .filter(parent__isnull=True, is_active=True)
            .annotate(product_count=Count(
                "products",
                filter=Q(products__is_active=True, products__deleted_at__isnull=True),
            ))
            .order_by("sort_order")
        )
        root_ids = [r.id for r in roots]
        children = list(
            self.category_repo.get_all()
            .filter(parent_id__in=root_ids, is_active=True)
            .annotate(product_count=Count(
                "products",
                filter=Q(products__is_active=True, products__deleted_at__isnull=True),
            ))
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
                "product_count": r.product_count,
                "children": [
                    {
                        "id": ch.id,
                        "name_uz": ch.name_uz,
                        "name_ru": ch.name_ru,
                        "image": ch.image,
                        "product_count": ch.product_count,
                    }
                    for ch in children_map.get(r.id, [])
                ],
            }
            for r in roots
        ]

    def get_featured(self, page=1, per_page=20):
        qs = self.product_repo.get_all().filter(is_active=True, is_featured=True).select_related("category")

        primary_img = Subquery(
            ProductImage.objects.filter(
                product=OuterRef("pk"), is_primary=True
            ).values("image")[:1]
        )
        qs = qs.annotate(primary_image=primary_img).order_by("sort_order")

        result = self.product_repo.paginate(qs, page, per_page)
        self._attach_discounts(result["items"])
        return result

    def search(self, query: str, page=1, per_page=20):
        qs = self.product_repo.get_all().filter(is_active=True).select_related("category")
        qs = self.product_repo.search(qs, query, ["name_uz", "name_ru", "description_uz", "description_ru"])

        primary_img = Subquery(
            ProductImage.objects.filter(
                product=OuterRef("pk"), is_primary=True
            ).values("image")[:1]
        )
        qs = qs.annotate(primary_image=primary_img).order_by("sort_order")

        result = self.product_repo.paginate(qs, page, per_page)
        self._attach_discounts(result["items"])
        return result

    def popular_products(self, page=1, per_page=20):
        sold_sq = Subquery(
            OrderItem.objects.filter(
                product_id=OuterRef("pk"),
                order__status__in=["completed", "delivered"],
            ).values("product_id").annotate(s=Sum("quantity")).values("s")[:1]
        )
        primary_img = Subquery(
            ProductImage.objects.filter(
                product=OuterRef("pk"), is_primary=True
            ).values("image")[:1]
        )

        qs = (
            self.product_repo.get_all()
            .filter(is_active=True)
            .select_related("category")
            .annotate(total_sold=sold_sq, primary_image=primary_img)
            .filter(total_sold__isnull=False)
            .order_by("-total_sold")
        )

        result = self.product_repo.paginate(qs, page, per_page)
        self._attach_discounts(result["items"])
        return result

    def _attach_discounts(self, products):
        """Batch-fetch active discounts for a page of products."""
        if not products:
            return

        now = timezone.now()
        product_ids = [p.id for p in products]
        category_ids = list({p.category_id for p in products})

        discounts = list(
            Discount.objects.filter(
                is_active=True, deleted_at__isnull=True,
            ).filter(
                Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                Q(expires_at__isnull=True) | Q(expires_at__gte=now),
            ).filter(
                Q(products__in=product_ids) | Q(categories__in=category_ids)
            ).distinct().prefetch_related("products", "categories")
        )

        if not discounts:
            return

        # Build lookup sets once
        discount_data = []
        for d in discounts:
            discount_data.append({
                "obj": d,
                "product_ids": set(d.products.values_list("id", flat=True)),
                "category_ids": set(d.categories.values_list("id", flat=True)),
            })

        for p in products:
            best_price = p.price
            for dd in discount_data:
                if p.id not in dd["product_ids"] and p.category_id not in dd["category_ids"]:
                    continue
                d = dd["obj"]
                if d.type == "percent":
                    disc = p.price * d.value / Decimal(100)
                    if d.max_discount:
                        disc = min(disc, d.max_discount)
                else:
                    disc = min(d.value, p.price)
                candidate = p.price - disc
                if candidate < best_price:
                    best_price = candidate
            if best_price < p.price:
                p._discounted_price = max(best_price, Decimal(0))
