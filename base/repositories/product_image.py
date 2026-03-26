from typing import Optional

from django.db.models import QuerySet

from base.models import ProductImage
from base.repositories.base import BaseRepository


class ProductImageRepository(BaseRepository[ProductImage]):
    model = ProductImage

    def get_by_product(self, product_id: int) -> QuerySet[ProductImage]:
        return self.get_queryset().filter(product_id=product_id)

    def get_primary(self, product_id: int) -> Optional[ProductImage]:
        return self.get_queryset().filter(
            product_id=product_id, is_primary=True
        ).first()

    def set_primary(self, image: ProductImage) -> ProductImage:
        self.get_queryset().filter(
            product_id=image.product_id, is_primary=True
        ).update(is_primary=False)
        image.is_primary = True
        image.save(update_fields=["is_primary"])
        return image

    def reorder(self, image_ids: list[int]) -> None:
        for index, pk in enumerate(image_ids):
            self.model.objects.filter(pk=pk).update(sort_order=index)

    def delete_by_product(self, product_id: int) -> int:
        count, _ = self.get_queryset().filter(product_id=product_id).delete()
        return count
