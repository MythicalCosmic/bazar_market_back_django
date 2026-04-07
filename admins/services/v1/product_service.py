from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Sum, Avg, Min, Max, Q, Exists, OuterRef, Subquery, F
from django.utils import timezone

from base.interfaces.product import IProductRepository
from base.interfaces.product_image import IProductImageRepository
from base.interfaces.category import ICategoryRepository
from base.interfaces.discount import IDiscountRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.product import CreateProductDTO, UpdateProductDTO
from base.models import Product, ProductImage, Discount, OrderItem


VALID_UNITS = {c[0] for c in Product.Unit.choices}

SEARCH_FIELDS = ["name_uz", "name_ru", "description_uz", "description_ru", "sku", "barcode"]

ORDER_FIELDS = {"sort_order", "price", "name_uz", "created_at", "stock_qty", "is_featured", "sku", "cost_price"}


class ProductService:
    def __init__(
        self,
        product_repository: IProductRepository,
        product_image_repository: IProductImageRepository,
        category_repository: ICategoryRepository,
        discount_repository: IDiscountRepository,
    ):
        self.product_repo = product_repository
        self.image_repo = product_image_repository
        self.category_repo = category_repository
        self.discount_repo = discount_repository

    def get_all(
        self,
        query=None,
        category_id=None,
        is_active=None,
        in_stock=None,
        is_featured=None,
        unit=None,
        min_price=None,
        max_price=None,
        has_discount=None,
        stock_status=None,
        has_sku=None,
        has_barcode=None,
        order_by="-created_at",
        page=1,
        per_page=20,
    ):
        qs = self.product_repo.get_all().select_related("category")

        qs = self.product_repo.search(qs, query, SEARCH_FIELDS)

        filters = {
            "is_active": is_active,
            "in_stock": in_stock,
            "is_featured": is_featured,
            "unit": unit,
            "category_id": category_id,
        }
        qs = self.product_repo.apply_filters(qs, filters)

        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)

        # stock_status: "out_of_stock", "low_stock", "in_stock", "unlimited"
        if stock_status == "out_of_stock":
            qs = qs.filter(Q(in_stock=False) | Q(stock_qty__isnull=False, stock_qty__lte=0))
        elif stock_status == "low_stock":
            qs = qs.filter(
                stock_qty__isnull=False,
                low_stock_threshold__isnull=False,
                stock_qty__lte=F("low_stock_threshold"),
                stock_qty__gt=0,
            )
        elif stock_status == "in_stock":
            qs = qs.filter(in_stock=True, stock_qty__isnull=False, stock_qty__gt=0)
        elif stock_status == "unlimited":
            qs = qs.filter(stock_qty__isnull=True)

        if has_sku is not None:
            qs = qs.filter(sku__isnull=not has_sku) if not has_sku else qs.exclude(sku__isnull=True).exclude(sku="")
        if has_barcode is not None:
            qs = qs.filter(barcode__isnull=not has_barcode) if not has_barcode else qs.exclude(barcode__isnull=True).exclude(barcode="")

        if has_discount is not None:
            now = timezone.now()
            discount_sq = Discount.objects.filter(
                Q(products=OuterRef("pk")) | Q(categories=OuterRef("category_id")),
                is_active=True,
                deleted_at__isnull=True,
            ).filter(
                Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                Q(expires_at__isnull=True) | Q(expires_at__gte=now),
            )
            qs = qs.annotate(_has_discount=Exists(discount_sq))
            qs = qs.filter(_has_discount=has_discount)

        primary_img = Subquery(
            ProductImage.objects.filter(
                product=OuterRef("pk"), is_primary=True
            ).values("image")[:1]
        )
        qs = qs.annotate(primary_image=primary_img)

        qs = self.product_repo.apply_ordering(qs, order_by, ORDER_FIELDS)

        return self.product_repo.paginate(qs, page, per_page)

    def get_by_id(self, product_id: int):
        product = (
            self.product_repo.get_all()
            .select_related("category")
            .prefetch_related("images")
            .filter(pk=product_id)
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
            )
            .filter(
                Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                Q(expires_at__isnull=True) | Q(expires_at__gte=now),
            )
            .distinct()
            .values("id", "name_uz", "type", "value", "max_discount")
        )

        product._current_discounts = discounts
        return product

    @transaction.atomic
    def create_product(self, dto: CreateProductDTO) -> dict:
        category = self.category_repo.get_by_id(dto.category_id)
        if not category:
            raise ValidationError("Category not found")

        if dto.unit not in VALID_UNITS:
            raise ValidationError(f"Invalid unit. Must be one of: {', '.join(VALID_UNITS)}")

        try:
            price = Decimal(dto.price)
            if price < 0:
                raise ValidationError("Price must be non-negative")
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid price")

        if dto.sku and self.product_repo.exists(sku=dto.sku):
            raise ValidationError("SKU already exists")
        if dto.barcode and self.product_repo.exists(barcode=dto.barcode):
            raise ValidationError("Barcode already exists")

        kwargs = {
            "category": category,
            "name_uz": dto.name_uz,
            "name_ru": dto.name_ru,
            "description_uz": dto.description_uz,
            "description_ru": dto.description_ru,
            "sku": dto.sku or None,
            "barcode": dto.barcode or None,
            "unit": dto.unit,
            "price": price,
            "step": Decimal(dto.step),
            "min_qty": Decimal(dto.min_qty),
            "in_stock": dto.in_stock,
            "sort_order": dto.sort_order,
            "is_active": dto.is_active,
            "is_featured": dto.is_featured,
        }
        if dto.cost_price is not None:
            kwargs["cost_price"] = Decimal(dto.cost_price)
        if dto.max_qty is not None:
            kwargs["max_qty"] = Decimal(dto.max_qty)
        if dto.stock_qty is not None:
            kwargs["stock_qty"] = Decimal(dto.stock_qty)
        if dto.low_stock_threshold is not None:
            kwargs["low_stock_threshold"] = Decimal(dto.low_stock_threshold)

        product = self.product_repo.create(**kwargs)

        if dto.images:
            images = [
                ProductImage(
                    product=product,
                    image=img["image"],
                    sort_order=i,
                    is_primary=img.get("is_primary", i == 0),
                )
                for i, img in enumerate(dto.images)
            ]
            self.image_repo.bulk_create(images)

        return {"id": product.id, "uuid": str(product.uuid), "name_uz": product.name_uz}

    def update_product(self, product_id: int, dto: UpdateProductDTO) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")

        data = dto.to_dict()

        if "category_id" in data:
            category = self.category_repo.get_by_id(data["category_id"])
            if not category:
                raise ValidationError("Category not found")

        if "unit" in data and data["unit"] not in VALID_UNITS:
            raise ValidationError(f"Invalid unit. Must be one of: {', '.join(VALID_UNITS)}")

        if "sku" in data and data["sku"] and data["sku"] != product.sku:
            if self.product_repo.exists(sku=data["sku"]):
                raise ValidationError("SKU already exists")
        if "barcode" in data and data["barcode"] and data["barcode"] != product.barcode:
            if self.product_repo.exists(barcode=data["barcode"]):
                raise ValidationError("Barcode already exists")

        for decimal_field in ("price", "cost_price", "step", "min_qty", "max_qty", "stock_qty", "low_stock_threshold"):
            if decimal_field in data and data[decimal_field] is not None:
                try:
                    data[decimal_field] = Decimal(str(data[decimal_field]))
                except (InvalidOperation, ValueError):
                    raise ValidationError(f"Invalid {decimal_field}")

        if "price" in data and data["price"] is not None and data["price"] < 0:
            raise ValidationError("Price must be non-negative")

        if data:
            self.product_repo.update(product, **data)

        return {"id": product.id, "name_uz": product.name_uz}

    def delete_product(self, product_id: int) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")

        pending_orders = OrderItem.objects.filter(
            product=product,
            order__status__in=["pending", "confirmed", "preparing", "delivering"],
        ).exists()
        if pending_orders:
            raise ValidationError("Cannot delete product with active orders")

        self.product_repo.soft_delete(product)
        return {"message": "Product deleted"}

    def restore_product(self, product_id: int) -> dict:
        product = self.product_repo.get_only_deleted().filter(pk=product_id).first()
        if not product:
            raise NotFoundError("Product not found or not deleted")

        category = self.category_repo.get_by_id(product.category_id)
        if not category:
            raise ValidationError("Category no longer exists")

        self.product_repo.restore(product)
        return {"message": "Product restored"}

    @transaction.atomic
    def reorder(self, product_ids: list[int]) -> dict:
        existing = set(
            self.product_repo.get_all()
            .filter(pk__in=product_ids)
            .values_list("pk", flat=True)
        )
        missing = set(product_ids) - existing
        if missing:
            raise ValidationError(f"Products not found: {missing}")

        self.product_repo.reorder(product_ids)
        return {"message": "Products reordered"}

    def activate(self, product_id: int) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")
        self.product_repo.activate(product)
        return {"message": "Product activated"}

    def deactivate(self, product_id: int) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")
        self.product_repo.deactivate(product)
        return {"message": "Product deactivated"}

    def feature(self, product_id: int) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")
        self.product_repo.feature(product)
        return {"message": "Product featured"}

    def unfeature(self, product_id: int) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")
        self.product_repo.unfeature(product)
        return {"message": "Product unfeatured"}

    def update_stock(self, product_id: int, stock_qty, in_stock=None) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")

        updates = {}
        if stock_qty is not None:
            try:
                updates["stock_qty"] = Decimal(str(stock_qty))
            except (InvalidOperation, ValueError):
                raise ValidationError("Invalid stock quantity")
        if in_stock is not None:
            updates["in_stock"] = in_stock

        if updates:
            self.product_repo.update(product, **updates)

        return {
            "id": product.id,
            "stock_qty": str(product.stock_qty) if product.stock_qty is not None else None,
            "in_stock": product.in_stock,
        }

    @transaction.atomic
    def add_images(self, product_id: int, images: list) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")

        if not images:
            raise ValidationError("No images provided")

        existing_count = self.image_repo.get_by_product(product_id).count()
        max_offset = existing_count

        has_primary = self.image_repo.get_primary(product_id) is not None

        objs = [
            ProductImage(
                product=product,
                image=img["image"],
                sort_order=max_offset + i,
                is_primary=(not has_primary and i == 0) if not img.get("is_primary") else img["is_primary"],
            )
            for i, img in enumerate(images)
        ]
        created = self.image_repo.bulk_create(objs)
        return {"added": len(created)}

    def remove_image(self, product_id: int, image_id: int) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")

        image = self.image_repo.get_queryset().filter(pk=image_id, product_id=product_id).first()
        if not image:
            raise NotFoundError("Image not found")

        was_primary = image.is_primary
        self.image_repo.delete(image)

        if was_primary:
            next_img = self.image_repo.get_queryset().filter(product_id=product_id).order_by("sort_order").first()
            if next_img:
                self.image_repo.set_primary(next_img)

        return {"message": "Image removed"}

    def reorder_images(self, product_id: int, image_ids: list[int]) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")

        existing = set(
            self.image_repo.get_by_product(product_id).values_list("pk", flat=True)
        )
        if set(image_ids) != existing:
            raise ValidationError("Image IDs must match all images of this product")

        self.image_repo.reorder(image_ids)
        return {"message": "Images reordered"}

    def set_primary_image(self, product_id: int, image_id: int) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")

        image = self.image_repo.get_queryset().filter(pk=image_id, product_id=product_id).first()
        if not image:
            raise NotFoundError("Image not found")

        self.image_repo.set_primary(image)
        return {"message": "Primary image set"}

    def assign_discounts(self, product_id: int, discount_ids: list[int]) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")

        existing = set(
            self.discount_repo.get_all()
            .filter(pk__in=discount_ids)
            .values_list("pk", flat=True)
        )
        missing = set(discount_ids) - existing
        if missing:
            raise ValidationError(f"Discounts not found: {missing}")

        for did in discount_ids:
            discount = self.discount_repo.get_by_id(did)
            self.discount_repo.add_products(discount, [product_id])

        return {"message": f"{len(discount_ids)} discount(s) assigned"}

    def remove_discounts(self, product_id: int, discount_ids: list[int]) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")

        for did in discount_ids:
            discount = self.discount_repo.get_by_id(did)
            if discount:
                self.discount_repo.remove_products(discount, [product_id])

        return {"message": f"{len(discount_ids)} discount(s) removed"}

    def stats(self, date_from=None, date_to=None, category_id=None) -> dict:
        qs = self.product_repo.get_all()

        if category_id:
            qs = qs.filter(category_id=category_id)

        total = qs.count()
        active = qs.filter(is_active=True).count()
        in_stock = qs.filter(in_stock=True, is_active=True).count()
        out_of_stock = qs.filter(in_stock=False, is_active=True).count()
        featured = qs.filter(is_featured=True).count()

        by_category = list(
            qs.values("category_id", "category__name_uz")
            .annotate(count=Count("id"))
            .order_by("-count")[:15]
        )

        by_unit = dict(
            qs.values_list("unit").annotate(c=Count("id")).values_list("unit", "c")
        )

        price_agg = qs.filter(is_active=True).aggregate(
            min_price=Min("price"),
            max_price=Max("price"),
            avg_price=Avg("price"),
        )

        low_stock = list(
            qs.filter(
                stock_qty__isnull=False,
                low_stock_threshold__isnull=False,
                stock_qty__lte=F("low_stock_threshold"),
                stock_qty__gt=0,
                is_active=True,
            )
            .order_by("stock_qty")
            .values("id", "name_uz", "sku", "stock_qty", "low_stock_threshold", "category__name_uz")[:20]
        )
        zero_stock = qs.filter(
            Q(in_stock=False) | Q(stock_qty__isnull=False, stock_qty__lte=0),
            is_active=True,
        ).count()
        unlimited_stock = qs.filter(stock_qty__isnull=True, is_active=True).count()
        without_sku = qs.filter(Q(sku__isnull=True) | Q(sku=""), is_active=True).count()
        without_barcode = qs.filter(Q(barcode__isnull=True) | Q(barcode=""), is_active=True).count()

        order_filter = Q(order_items__order__status__in=["completed", "delivered"])
        if date_from:
            order_filter &= Q(order_items__order__created_at__gte=date_from)
        if date_to:
            order_filter &= Q(order_items__order__created_at__lte=date_to)

        top_by_revenue = list(
            qs.annotate(
                revenue=Sum("order_items__total", filter=order_filter),
                qty_sold=Sum("order_items__quantity", filter=order_filter),
            )
            .filter(revenue__isnull=False)
            .order_by("-revenue")
            .values("id", "name_uz", "category__name_uz", "revenue", "qty_sold")[:10]
        )

        top_by_quantity = list(
            qs.annotate(
                qty_sold=Sum("order_items__quantity", filter=order_filter),
                order_count=Count("order_items__order", filter=order_filter, distinct=True),
            )
            .filter(qty_sold__isnull=False)
            .order_by("-qty_sold")
            .values("id", "name_uz", "category__name_uz", "qty_sold", "order_count")[:10]
        )

        never_ordered = qs.filter(is_active=True).annotate(
            oi_count=Count("order_items")
        ).filter(oi_count=0).count()

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "in_stock": in_stock,
            "out_of_stock": out_of_stock,
            "zero_stock": zero_stock,
            "unlimited_stock": unlimited_stock,
            "featured": featured,
            "never_ordered": never_ordered,
            "without_sku": without_sku,
            "without_barcode": without_barcode,
            "by_category": [
                {"category_id": s["category_id"], "category": s["category__name_uz"], "count": s["count"]}
                for s in by_category
            ],
            "by_unit": by_unit,
            "price_range": {
                "min": str(price_agg["min_price"] or 0),
                "max": str(price_agg["max_price"] or 0),
                "avg": str(round(price_agg["avg_price"] or 0, 2)),
            },
            "low_stock": [
                {
                    "id": s["id"],
                    "name": s["name_uz"],
                    "sku": s["sku"],
                    "stock_qty": str(s["stock_qty"]),
                    "threshold": str(s["low_stock_threshold"]),
                    "category": s["category__name_uz"],
                }
                for s in low_stock
            ],
            "top_by_revenue": [
                {
                    "id": s["id"],
                    "name": s["name_uz"],
                    "category": s["category__name_uz"],
                    "revenue": str(s["revenue"] or 0),
                    "qty_sold": str(s["qty_sold"] or 0),
                }
                for s in top_by_revenue
            ],
            "top_by_quantity": [
                {
                    "id": s["id"],
                    "name": s["name_uz"],
                    "category": s["category__name_uz"],
                    "qty_sold": str(s["qty_sold"] or 0),
                    "order_count": s["order_count"],
                }
                for s in top_by_quantity
            ],
        }
