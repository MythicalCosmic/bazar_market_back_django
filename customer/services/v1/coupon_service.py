from decimal import Decimal

from django.utils import timezone

from base.interfaces.coupon import ICouponRepository, ICouponUsageRepository
from base.exceptions import ValidationError


class CustomerCouponService:
    def __init__(
        self,
        coupon_repository: ICouponRepository,
        coupon_usage_repository: ICouponUsageRepository,
    ):
        self.coupon_repo = coupon_repository
        self.usage_repo = coupon_usage_repository

    def validate_coupon(self, user_id: int, code: str, subtotal: Decimal) -> dict:
        coupon = self.coupon_repo.get_by_code(code.upper())
        if not coupon:
            raise ValidationError("Invalid coupon code")

        if not coupon.is_active:
            raise ValidationError("This coupon is no longer active")

        now = timezone.now()
        if coupon.starts_at and coupon.starts_at > now:
            raise ValidationError("This coupon is not yet valid")
        if coupon.expires_at and coupon.expires_at < now:
            raise ValidationError("This coupon has expired")

        if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
            raise ValidationError("This coupon has reached its usage limit")

        user_usage = self.usage_repo.get_user_usage_count(coupon.id, user_id)
        if user_usage >= coupon.per_user_limit:
            raise ValidationError("You have already used this coupon")

        if coupon.min_order and subtotal < coupon.min_order:
            raise ValidationError(f"Minimum order amount is {coupon.min_order}")

        discount_amount = self.calculate_discount(coupon, subtotal)

        return {
            "valid": True,
            "code": coupon.code,
            "type": coupon.type,
            "value": str(coupon.value),
            "discount_amount": str(discount_amount),
            "max_discount": str(coupon.max_discount) if coupon.max_discount else None,
        }

    @staticmethod
    def calculate_discount(coupon, subtotal: Decimal) -> Decimal:
        if coupon.type == "percent":
            discount = subtotal * coupon.value / 100
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else:
            discount = min(coupon.value, subtotal)
        return discount
