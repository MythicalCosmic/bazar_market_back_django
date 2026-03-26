from typing import Optional

from django.db.models import QuerySet, Q, F
from django.utils import timezone

from base.models import Coupon, CouponUsage
from base.repositories.base import BaseRepository


class CouponRepository(BaseRepository[Coupon]):
    model = Coupon

    def get_by_code(self, code: str) -> Optional[Coupon]:
        return self.get_queryset().filter(code=code).first()

    def get_active(self) -> QuerySet[Coupon]:
        return self.get_queryset().filter(is_active=True)

    def get_valid(self) -> QuerySet[Coupon]:
        now = timezone.now()
        return self.get_active().filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        ).filter(
            Q(usage_limit__isnull=True) | Q(used_count__lt=F("usage_limit"))
        )

    def is_valid(self, code: str) -> bool:
        return self.get_valid().filter(code=code).exists()

    def increment_usage(self, coupon: Coupon) -> int:
        return self.model.objects.filter(pk=coupon.pk).update(
            used_count=F("used_count") + 1
        )

    def decrement_usage(self, coupon: Coupon) -> int:
        return self.model.objects.filter(
            pk=coupon.pk, used_count__gt=0
        ).update(used_count=F("used_count") - 1)

    def deactivate(self, coupon: Coupon) -> Coupon:
        return self.update(coupon, is_active=False)

    def activate(self, coupon: Coupon) -> Coupon:
        return self.update(coupon, is_active=True)


class CouponUsageRepository(BaseRepository[CouponUsage]):
    model = CouponUsage

    def get_by_coupon(self, coupon_id: int) -> QuerySet[CouponUsage]:
        return self.get_queryset().filter(coupon_id=coupon_id)

    def get_by_user(self, user_id: int) -> QuerySet[CouponUsage]:
        return self.get_queryset().filter(user_id=user_id)

    def get_user_usage_count(self, coupon_id: int, user_id: int) -> int:
        return self.get_queryset().filter(
            coupon_id=coupon_id, user_id=user_id
        ).count()

    def has_used(self, coupon_id: int, user_id: int) -> bool:
        return self.get_queryset().filter(
            coupon_id=coupon_id, user_id=user_id
        ).exists()

    def record_usage(
        self, coupon_id: int, user_id: int, order_id: int, discount_amount
    ) -> CouponUsage:
        return self.create(
            coupon_id=coupon_id,
            user_id=user_id,
            order_id=order_id,
            discount_amount=discount_amount,
        )
