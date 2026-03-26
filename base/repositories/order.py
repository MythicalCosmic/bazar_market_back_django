from typing import Optional
from datetime import datetime

from django.db.models import QuerySet, Sum, Count
from django.utils import timezone

from base.models import Order, OrderItem, OrderStatusLog
from base.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    model = Order

    def get_by_uuid(self, uuid) -> Optional[Order]:
        return self.get_queryset().filter(uuid=uuid).first()

    def get_by_order_number(self, order_number: str) -> Optional[Order]:
        return self.get_queryset().filter(order_number=order_number).first()

    def get_by_user(self, user_id: int) -> QuerySet[Order]:
        return self.get_queryset().filter(user_id=user_id)

    def get_by_status(self, status: str) -> QuerySet[Order]:
        return self.get_queryset().filter(status=status)

    def get_active_orders(self) -> QuerySet[Order]:
        return self.get_queryset().exclude(
            status__in=[Order.Status.COMPLETED, Order.Status.CANCELLED]
        )

    def get_active_by_user(self, user_id: int) -> QuerySet[Order]:
        return self.get_active_orders().filter(user_id=user_id)

    def get_user_history(self, user_id: int) -> QuerySet[Order]:
        return self.get_by_user(user_id).filter(
            status__in=[Order.Status.COMPLETED, Order.Status.CANCELLED]
        )

    def update_status(self, order: Order, status: str) -> Order:
        now = timezone.now()
        kwargs: dict = {"status": status}
        if status == Order.Status.CONFIRMED:
            kwargs["confirmed_at"] = now
        elif status == Order.Status.DELIVERED:
            kwargs["delivered_at"] = now
        elif status == Order.Status.COMPLETED:
            kwargs["completed_at"] = now
        elif status == Order.Status.CANCELLED:
            kwargs["cancelled_at"] = now
        return self.update(order, **kwargs)

    def update_payment_status(self, order: Order, payment_status: str) -> Order:
        return self.update(order, payment_status=payment_status)

    def get_daily_orders(self, date) -> QuerySet[Order]:
        return self.get_queryset().filter(created_at__date=date)

    def get_orders_in_range(
        self, start: datetime, end: datetime
    ) -> QuerySet[Order]:
        return self.get_queryset().filter(created_at__range=(start, end))

    def get_pending(self) -> QuerySet[Order]:
        return self.get_by_status(Order.Status.PENDING)

    def get_revenue_in_range(self, start: datetime, end: datetime) -> dict:
        return self.get_queryset().filter(
            created_at__range=(start, end),
            status=Order.Status.COMPLETED,
        ).aggregate(
            total_revenue=Sum("total"),
            order_count=Count("id"),
        )

    def cancel(self, order: Order, reason: str = "") -> Order:
        return self.update(
            order,
            status=Order.Status.CANCELLED,
            cancelled_at=timezone.now(),
            cancel_reason=reason,
        )


class OrderItemRepository(BaseRepository[OrderItem]):
    model = OrderItem

    def get_by_order(self, order_id: int) -> QuerySet[OrderItem]:
        return self.get_queryset().filter(order_id=order_id).select_related("product")

    def bulk_create_items(self, order: Order, items: list[dict]) -> list[OrderItem]:
        order_items = [OrderItem(order=order, **item) for item in items]
        return self.bulk_create(order_items)

    def get_order_total(self, order_id: int) -> dict:
        return self.get_queryset().filter(order_id=order_id).aggregate(
            total=Sum("total"),
            item_count=Count("id"),
        )


class OrderStatusLogRepository(BaseRepository[OrderStatusLog]):
    model = OrderStatusLog

    def get_by_order(self, order_id: int) -> QuerySet[OrderStatusLog]:
        return self.get_queryset().filter(order_id=order_id)

    def log_transition(
        self,
        order_id: int,
        from_status: str,
        to_status: str,
        changed_by_id: Optional[int] = None,
        note: str = "",
    ) -> OrderStatusLog:
        return self.create(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            changed_by_id=changed_by_id,
            note=note,
        )

    def get_latest(self, order_id: int) -> Optional[OrderStatusLog]:
        return self.get_by_order(order_id).last()
