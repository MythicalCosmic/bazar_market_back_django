from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import Coupon, CouponUsage


class ICouponRepository(IBaseRepository[Coupon]):

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Coupon]: ...

    @abstractmethod
    def get_active(self) -> QuerySet[Coupon]: ...

    @abstractmethod
    def get_valid(self) -> QuerySet[Coupon]: ...

    @abstractmethod
    def is_valid(self, code: str) -> bool: ...

    @abstractmethod
    def increment_usage(self, coupon: Coupon) -> int: ...

    @abstractmethod
    def decrement_usage(self, coupon: Coupon) -> int: ...

    @abstractmethod
    def deactivate(self, coupon: Coupon) -> Coupon: ...

    @abstractmethod
    def activate(self, coupon: Coupon) -> Coupon: ...


class ICouponUsageRepository(IBaseRepository[CouponUsage]):

    @abstractmethod
    def get_by_coupon(self, coupon_id: int) -> QuerySet[CouponUsage]: ...

    @abstractmethod
    def get_by_user(self, user_id: int) -> QuerySet[CouponUsage]: ...

    @abstractmethod
    def get_user_usage_count(self, coupon_id: int, user_id: int) -> int: ...

    @abstractmethod
    def has_used(self, coupon_id: int, user_id: int) -> bool: ...

    @abstractmethod
    def record_usage(
        self, coupon_id: int, user_id: int, order_id: int, discount_amount
    ) -> CouponUsage: ...
