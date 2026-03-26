from typing import Optional
from decimal import Decimal

from django.db.models import QuerySet, F, Q

from base.models import Product
from base.repositories.base import SoftDeleteRepository


class ProductRepository(SoftDeleteRepository[Product]):
    model = Product

    def get_by_uuid(self, uuid) -> Optional[Product]:
        return self.get_queryset().filter(uuid=uuid).first()

    def get_by_category(self, category_id: int) -> QuerySet[Product]:
        return self.get_queryset().filter(category_id=category_id)

    def get_active(self) -> QuerySet[Product]:
        return self.get_queryset().filter(is_active=True)

    def get_available(self) -> QuerySet[Product]:
        return self.get_queryset().filter(is_active=True, in_stock=True)

    def get_available_by_category(self, category_id: int) -> QuerySet[Product]:
        return self.get_available().filter(category_id=category_id)

    def search(self, query: str) -> QuerySet[Product]:
        return self.get_queryset().filter(
            Q(name_uz__icontains=query) | Q(name_ru__icontains=query)
        )

    def search_available(self, query: str) -> QuerySet[Product]:
        return self.get_available().filter(
            Q(name_uz__icontains=query) | Q(name_ru__icontains=query)
        )

    def update_stock(self, product: Product, quantity: Decimal) -> Product:
        return self.update(product, stock_qty=quantity)

    def decrease_stock(self, product_id: int, quantity: Decimal) -> int:
        return self.model.objects.filter(
            pk=product_id, stock_qty__isnull=False, stock_qty__gte=quantity
        ).update(stock_qty=F("stock_qty") - quantity)

    def increase_stock(self, product_id: int, quantity: Decimal) -> int:
        return self.model.objects.filter(
            pk=product_id, stock_qty__isnull=False
        ).update(stock_qty=F("stock_qty") + quantity)

    def mark_out_of_stock(self, product: Product) -> Product:
        return self.update(product, in_stock=False)

    def mark_in_stock(self, product: Product) -> Product:
        return self.update(product, in_stock=True)

    def deactivate(self, product: Product) -> Product:
        return self.update(product, is_active=False)

    def activate(self, product: Product) -> Product:
        return self.update(product, is_active=True)

    def reorder(self, product_ids: list[int]) -> None:
        for index, pk in enumerate(product_ids):
            self.model.objects.filter(pk=pk).update(sort_order=index)

    def get_by_price_range(
        self, min_price: Decimal, max_price: Decimal
    ) -> QuerySet[Product]:
        return self.get_available().filter(price__gte=min_price, price__lte=max_price)
