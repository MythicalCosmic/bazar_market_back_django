from abc import abstractmethod
from datetime import datetime
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import Order, OrderItem, OrderStatusLog


class IOrderRepository(IBaseRepository[Order]):

    @abstractmethod
    def get_by_uuid(self, uuid) -> Optional[Order]: ...

    @abstractmethod
    def get_by_order_number(self, order_number: str) -> Optional[Order]: ...

    @abstractmethod
    def get_by_user(self, user_id: int) -> QuerySet[Order]: ...

    @abstractmethod
    def get_by_status(self, status: str) -> QuerySet[Order]: ...

    @abstractmethod
    def get_active_orders(self) -> QuerySet[Order]: ...

    @abstractmethod
    def get_active_by_user(self, user_id: int) -> QuerySet[Order]: ...

    @abstractmethod
    def get_user_history(self, user_id: int) -> QuerySet[Order]: ...

    @abstractmethod
    def update_status(self, order: Order, status: str) -> Order: ...

    @abstractmethod
    def update_payment_status(self, order: Order, payment_status: str) -> Order: ...

    @abstractmethod
    def get_daily_orders(self, date) -> QuerySet[Order]: ...

    @abstractmethod
    def get_orders_in_range(
        self, start: datetime, end: datetime
    ) -> QuerySet[Order]: ...

    @abstractmethod
    def get_pending(self) -> QuerySet[Order]: ...

    @abstractmethod
    def get_revenue_in_range(self, start: datetime, end: datetime) -> dict: ...

    @abstractmethod
    def cancel(self, order: Order, reason: str = "") -> Order: ...


class IOrderItemRepository(IBaseRepository[OrderItem]):

    @abstractmethod
    def get_by_order(self, order_id: int) -> QuerySet[OrderItem]: ...

    @abstractmethod
    def bulk_create_items(
        self, order: Order, items: list[dict]
    ) -> list[OrderItem]: ...

    @abstractmethod
    def get_order_total(self, order_id: int) -> dict: ...


class IOrderStatusLogRepository(IBaseRepository[OrderStatusLog]):

    @abstractmethod
    def get_by_order(self, order_id: int) -> QuerySet[OrderStatusLog]: ...

    @abstractmethod
    def log_transition(
        self,
        order_id: int,
        from_status: str,
        to_status: str,
        changed_by_id: Optional[int] = None,
        note: str = "",
    ) -> OrderStatusLog: ...

    @abstractmethod
    def get_latest(self, order_id: int) -> Optional[OrderStatusLog]: ...
