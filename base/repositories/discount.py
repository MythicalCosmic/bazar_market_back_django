from typing import Optional

from django.db.models import QuerySet, Q
from django.utils import timezone

from base.models import Discount
from base.repositories.base import SoftDeleteRepository


class DiscountRepository(SoftDeleteRepository[Discount]):
    model = Discount

    def get_by_uuid(self, uuid) -> Optional[Discount]:
        return self.get_queryset().filter(uuid=uuid).first()

    def get_active(self) -> QuerySet[Discount]:
        return self.get_queryset().filter(is_active=True)

    def get_current(self) -> QuerySet[Discount]:
        now = timezone.now()
        return self.get_active().filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        )

    def get_for_product(self, product_id: int) -> QuerySet[Discount]:
        return self.get_current().filter(products__id=product_id)

    def get_for_category(self, category_id: int) -> QuerySet[Discount]:
        return self.get_current().filter(categories__id=category_id)

    def get_for_product_or_category(
        self, product_id: int, category_id: int
    ) -> QuerySet[Discount]:
        return self.get_current().filter(
            Q(products__id=product_id) | Q(categories__id=category_id)
        ).distinct()

    def add_products(self, discount: Discount, product_ids: list[int]) -> None:
        discount.products.add(*product_ids)

    def remove_products(self, discount: Discount, product_ids: list[int]) -> None:
        discount.products.remove(*product_ids)

    def set_products(self, discount: Discount, product_ids: list[int]) -> None:
        discount.products.set(product_ids)

    def add_categories(self, discount: Discount, category_ids: list[int]) -> None:
        discount.categories.add(*category_ids)

    def remove_categories(self, discount: Discount, category_ids: list[int]) -> None:
        discount.categories.remove(*category_ids)

    def set_categories(self, discount: Discount, category_ids: list[int]) -> None:
        discount.categories.set(category_ids)

    def deactivate(self, discount: Discount) -> Discount:
        return self.update(discount, is_active=False)

    def activate(self, discount: Discount) -> Discount:
        return self.update(discount, is_active=True)
