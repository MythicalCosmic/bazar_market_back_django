from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Sum, Q
from django.utils import timezone

from base.interfaces.coupon import ICouponRepository, ICouponUsageRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.coupon import CreateCouponDTO, UpdateCouponDTO
from base.models import Coupon
from django.utils.dateparse import parse_datetime

VALID_TYPES = {c[0] for c in Coupon.Type.choices}


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
        raise ValidationError("Unsupportred type for datetime")
    
    #make timezone aware if naiva
    if dt.tzinfo is None:
        dt = timezone.make_aware(dt)
    return dt


class CouponService:
    def __init__(
        self,
        coupon_repository: ICouponRepository,
        coupon_usage_repository: ICouponUsageRepository,
    ):
        self.coupon_repo = coupon_repository
        self.usage_repo = coupon_usage_repository

    def get_all(self, query=None, is_active=None, type=None, valid_only=False, order_by="-created_at", page=1, per_page=20):
        qs = self.coupon_repo.get_all()
        qs = self.coupon_repo.search(qs, query, ["code"])
        qs = self.coupon_repo.apply_filters(qs, {"is_active": is_active, "type": type})

        if valid_only:
            now = timezone.now()
            from django.db.models import F
            qs = qs.filter(
                is_active=True,
            ).filter(
                Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                Q(expires_at__isnull=True) | Q(expires_at__gte=now),
            ).filter(
                Q(usage_limit__isnull=True) | Q(used_count__lt=F("usage_limit"))
            )

        qs = self.coupon_repo.apply_ordering(qs, order_by, {"created_at", "code", "used_count", "value"})
        return self.coupon_repo.paginate(qs, page, per_page)

    def get_by_id(self, coupon_id: int):
        coupon = self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            return None
        coupon._usages = list(
            self.usage_repo.get_by_coupon(coupon_id)
            .select_related("user", "order")
            .order_by("-used_at")[:50]
        )
        return coupon

    def create_coupon(self, dto: CreateCouponDTO) -> dict:
        if dto.type not in VALID_TYPES:
            raise ValidationError(f"Invalid type. Must be one of: {', '.join(VALID_TYPES)}")

        if self.coupon_repo.exists(code=dto.code):
            raise ValidationError(f"Code '{dto.code}' already exists")

        try:
            value = Decimal(dto.value)
            if value <= 0:
                raise ValidationError("Value must be positive")
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid value")
        current_time = timezone.now()
        expires_at = _parse_dt(dto.expires_at)
        if expires_at and expires_at < current_time:
            raise ValidationError("Expires at cannot be in the past")
        
        kwargs = {
            "code": dto.code.upper(),
            "type": dto.type,
            "value": value,
            "per_user_limit": dto.per_user_limit,
            "starts_at": _parse_dt(dto.starts_at),
            "expires_at": _parse_dt(dto.expires_at),
            "is_active": dto.is_active,
        }
        if dto.min_order is not None:
            kwargs["min_order"] = Decimal(dto.min_order)
        if dto.max_discount is not None:
            kwargs["max_discount"] = Decimal(dto.max_discount)
        if dto.usage_limit is not None:
            kwargs["usage_limit"] = dto.usage_limit

        coupon = self.coupon_repo.create(**kwargs)
        return {"id": coupon.id, "code": coupon.code}

    def update_coupon(self, coupon_id: int, dto: UpdateCouponDTO) -> dict:
        coupon = self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundError("Coupon not found")

        data = dto.to_dict()

        if "type" in data and data["type"] not in VALID_TYPES:
            raise ValidationError("Invalid type")

        if "code" in data and data["code"] != coupon.code:
            if self.coupon_repo.exists(code=data["code"]):
                raise ValidationError(f"Code '{data['code']}' already exists")
            data["code"] = data["code"].upper()

        for decimal_field in ("value", "min_order", "max_discount"):
            if decimal_field in data and data[decimal_field] is not None:
                try:
                    data[decimal_field] = Decimal(str(data[decimal_field]))
                except (InvalidOperation, ValueError):
                    raise ValidationError(f"Invalid {decimal_field}")

        for dt_field in ("starts_at", "expires_at"):
            if dt_field in data:
                data[dt_field] = _parse_dt(data[dt_field])

        if data:
            self.coupon_repo.update(coupon, **data)

        return {"id": coupon.id, "code": coupon.code}

    def delete_coupon(self, coupon_id: int) -> dict:
        coupon = self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundError("Coupon not found")

        if coupon.used_count > 0:
            raise ValidationError("Cannot delete coupon that has been used. Deactivate instead.")

        self.coupon_repo.delete(coupon)
        return {"message": "Coupon deleted"}

    def activate(self, coupon_id: int) -> dict:
        coupon = self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundError("Coupon not found")
        self.coupon_repo.activate(coupon)
        return {"message": "Coupon activated"}

    def deactivate(self, coupon_id: int) -> dict:
        coupon = self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundError("Coupon not found")
        self.coupon_repo.deactivate(coupon)
        return {"message": "Coupon deactivated"}

    def stats(self, date_from=None, date_to=None) -> dict:
        qs = self.coupon_repo.get_all()
        total = qs.count()
        active = qs.filter(is_active=True).count()

        now = timezone.now()
        from django.db.models import F
        valid = qs.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        ).filter(
            Q(usage_limit__isnull=True) | Q(used_count__lt=F("usage_limit"))
        ).count()

        usage_qs = self.usage_repo.get_all()
        if date_from:
            usage_qs = usage_qs.filter(used_at__gte=date_from)
        if date_to:
            usage_qs = usage_qs.filter(used_at__lte=date_to)

        usage_agg = usage_qs.aggregate(
            total_uses=Count("id"),
            total_discount=Sum("discount_amount"),
        )

        top_used = list(
            qs.filter(used_count__gt=0)
            .order_by("-used_count")
            .values("id", "code", "type", "value", "used_count", "usage_limit")[:10]
        )

        expired = qs.filter(expires_at__lt=now).count()

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "currently_valid": valid,
            "expired": expired,
            "total_uses": usage_agg["total_uses"] or 0,
            "total_discount_given": str(usage_agg["total_discount"] or 0),
            "top_used": [
                {
                    "id": c["id"],
                    "code": c["code"],
                    "type": c["type"],
                    "value": str(c["value"]),
                    "used_count": c["used_count"],
                    "usage_limit": c["usage_limit"],
                }
                for c in top_used
            ],
        }
