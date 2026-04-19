from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Q
from django.utils import timezone

from base.interfaces.discount import IDiscountRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.discount import CreateDiscountDTO, UpdateDiscountDTO
from base.models import Discount
from django.utils.dateparse import parse_datetime


VALID_TYPES = {c[0] for c in Discount.Type.choices}


def _parse_dt(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val
    elif isinstance(val, str):
        dt = parse_datetime(val)
        if dt is None:
            raise ValueError("Invalid datetime format")
    else:
        raise ValueError("Unsupported type for datetime")

    if dt.tzinfo is None:
        dt = timezone.make_aware(dt)
    return dt


class DiscountService:
    def __init__(self, discount_repository: IDiscountRepository):
        self.discount_repo = discount_repository

    def get_all(self, query=None, is_active=None, type=None, current_only=False, order_by="-created_at", page=1, per_page=20):
        qs = self.discount_repo.get_all()
        qs = self.discount_repo.search(qs, query, ["name_uz", "name_ru"])
        qs = self.discount_repo.apply_filters(qs, {"is_active": is_active, "type": type})

        if current_only:
            now = timezone.now()
            qs = qs.filter(is_active=True).filter(
                Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                Q(expires_at__isnull=True) | Q(expires_at__gte=now),
            )

        qs = self.discount_repo.apply_ordering(qs, order_by, {"created_at", "name_uz", "value"})
        qs = qs.annotate(
            product_count=Count("products", distinct=True),
            category_count=Count("categories", distinct=True),
        )
        return self.discount_repo.paginate(qs, page, per_page)

    def get_by_id(self, discount_id: int):
        discount = self.discount_repo.get_all().filter(pk=discount_id).first()
        if not discount:
            return None

        discount._products = list(
            discount.products.filter(deleted_at__isnull=True)
            .values("id", "name_uz", "price")[:50]
        )
        discount._categories = list(
            discount.categories.filter(deleted_at__isnull=True)
            .values("id", "name_uz")[:50]
        )
        return discount

    def create_discount(self, dto: CreateDiscountDTO) -> dict:
        if dto.type not in VALID_TYPES:
            raise ValidationError(f"Invalid type. Must be one of: {', '.join(VALID_TYPES)}")

        try:
            value = Decimal(dto.value)
            if value <= 0:
                raise ValidationError("Value must be positive")
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid value")

        if dto.type == "percent" and value > 100:
            raise ValidationError("Percent discount cannot exceed 100")

        if dto.max_discount is not None:
            try:
                max_discount = Decimal(dto.max_discount)
                if max_discount <= 0:
                    raise ValidationError("max_discount must be positive")
            except (InvalidOperation, ValueError):
                raise ValidationError("Invalid max_discount")
        else:
            max_discount = None

        starts_at = _parse_dt(dto.starts_at)
        expires_at = _parse_dt(dto.expires_at)

        now = timezone.now()
        if expires_at and expires_at < now:
            raise ValidationError("expires_at cannot be in the past")
        if starts_at and expires_at and starts_at >= expires_at:
            raise ValidationError("starts_at must be before expires_at")

        kwargs = {
            "name_uz": dto.name_uz,
            "name_ru": dto.name_ru,
            "type": dto.type,
            "value": value,
            "starts_at": starts_at,
            "expires_at": expires_at,
            "is_active": dto.is_active,
        }
        if max_discount is not None:
            kwargs["max_discount"] = max_discount

        discount = self.discount_repo.create(**kwargs)

        if dto.product_ids:
            self.discount_repo.add_products(discount, dto.product_ids)
        if dto.category_ids:
            self.discount_repo.add_categories(discount, dto.category_ids)

        return {"id": discount.id, "name_uz": discount.name_uz}

    def update_discount(self, discount_id: int, dto: UpdateDiscountDTO) -> dict:
        discount = self.discount_repo.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Discount not found")

        data = dto.to_dict()

        if "type" in data and data["type"] not in VALID_TYPES:
            raise ValidationError("Invalid type")

        for decimal_field in ("value", "max_discount"):
            if decimal_field in data and data[decimal_field] is not None:
                try:
                    data[decimal_field] = Decimal(str(data[decimal_field]))
                    if data[decimal_field] <= 0:
                        raise ValidationError(f"{decimal_field} must be positive")
                except (InvalidOperation, ValueError):
                    raise ValidationError(f"Invalid {decimal_field}")

        effective_type = data.get("type", discount.type)
        effective_value = data.get("value", discount.value)
        if effective_type == "percent" and effective_value > 100:
            raise ValidationError("Percent discount cannot exceed 100")

        for dt_field in ("starts_at", "expires_at"):
            if dt_field in data:
                data[dt_field] = _parse_dt(data[dt_field])

        effective_starts = data.get("starts_at", discount.starts_at)
        effective_expires = data.get("expires_at", discount.expires_at)

        if effective_expires and effective_expires < timezone.now():
            raise ValidationError("expires_at cannot be in the past")
        if effective_starts and effective_expires and effective_starts >= effective_expires:
            raise ValidationError("starts_at must be before expires_at")

        if data:
            self.discount_repo.update(discount, **data)

        return {"id": discount.id, "name_uz": discount.name_uz}

    def delete_discount(self, discount_id: int) -> dict:
        discount = self.discount_repo.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Discount not found")
        self.discount_repo.soft_delete(discount)
        return {"message": "Discount deleted"}

    def restore_discount(self, discount_id: int) -> dict:
        discount = self.discount_repo.get_only_deleted().filter(pk=discount_id).first()
        if not discount:
            raise NotFoundError("Discount not found or not deleted")
        self.discount_repo.restore(discount)
        return {"message": "Discount restored"}

    def activate(self, discount_id: int) -> dict:
        discount = self.discount_repo.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Discount not found")
        self.discount_repo.activate(discount)
        return {"message": "Discount activated"}

    def deactivate(self, discount_id: int) -> dict:
        discount = self.discount_repo.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Discount not found")
        self.discount_repo.deactivate(discount)
        return {"message": "Discount deactivated"}

    def set_products(self, discount_id: int, product_ids: list[int]) -> dict:
        discount = self.discount_repo.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Discount not found")
        self.discount_repo.set_products(discount, product_ids)
        return {"message": f"{len(product_ids)} product(s) set"}

    def add_products(self, discount_id: int, product_ids: list[int]) -> dict:
        discount = self.discount_repo.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Discount not found")
        self.discount_repo.add_products(discount, product_ids)
        return {"message": f"{len(product_ids)} product(s) added"}

    def remove_products(self, discount_id: int, product_ids: list[int]) -> dict:
        discount = self.discount_repo.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Discount not found")
        self.discount_repo.remove_products(discount, product_ids)
        return {"message": f"{len(product_ids)} product(s) removed"}

    def set_categories(self, discount_id: int, category_ids: list[int]) -> dict:
        discount = self.discount_repo.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Discount not found")
        self.discount_repo.set_categories(discount, category_ids)
        return {"message": f"{len(category_ids)} category(ies) set"}

    def add_categories(self, discount_id: int, category_ids: list[int]) -> dict:
        discount = self.discount_repo.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Discount not found")
        self.discount_repo.add_categories(discount, category_ids)
        return {"message": f"{len(category_ids)} category(ies) added"}

    def remove_categories(self, discount_id: int, category_ids: list[int]) -> dict:
        discount = self.discount_repo.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Discount not found")
        self.discount_repo.remove_categories(discount, category_ids)
        return {"message": f"{len(category_ids)} category(ies) removed"}

    def stats(self) -> dict:
        qs = self.discount_repo.get_all()
        now = timezone.now()
        total = qs.count()
        active = qs.filter(is_active=True).count()
        current = qs.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        ).count()

        by_type = dict(
            qs.values_list("type").annotate(c=Count("id")).values_list("type", "c")
        )

        with_products = qs.annotate(pc=Count("products", distinct=True)).filter(pc__gt=0).count()
        with_categories = qs.annotate(cc=Count("categories", distinct=True)).filter(cc__gt=0).count()

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "currently_active": current,
            "by_type": by_type,
            "with_products": with_products,
            "with_categories": with_categories,
        }