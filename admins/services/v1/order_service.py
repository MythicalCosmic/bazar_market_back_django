from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum, Avg, Min, Max, Q, F, ExpressionWrapper, DurationField
from django.db.models.functions import TruncDate, ExtractHour
from django.utils import timezone

from base.interfaces.order import IOrderRepository, IOrderItemRepository, IOrderStatusLogRepository
from base.interfaces.product import IProductRepository
from base.interfaces.setting import ISettingRepository
from base.exceptions import NotFoundError, ValidationError
from base.models import Order, User


VALID_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"preparing", "cancelled"},
    "preparing": {"delivering", "cancelled"},
    "delivering": {"delivered", "cancelled"},
    "delivered": {"completed"},
    "completed": set(),
    "cancelled": set(),
}

VALID_STATUSES = {c[0] for c in Order.Status.choices}
VALID_PAYMENT_STATUSES = {c[0] for c in Order.PaymentStatus.choices}

SEARCH_FIELDS = ["order_number", "user__first_name", "user__last_name", "user__phone"]

ORDER_FIELDS = {"created_at", "total", "status", "order_number"}

STOCK_DEDUCTED_STATUSES = {"confirmed", "preparing", "delivering", "delivered", "completed"}


class OrderService:
    def __init__(
        self,
        order_repository: IOrderRepository,
        order_item_repository: IOrderItemRepository,
        order_status_log_repository: IOrderStatusLogRepository,
        product_repository: IProductRepository,
        setting_repository: ISettingRepository,
    ):
        self.order_repo = order_repository
        self.item_repo = order_item_repository
        self.log_repo = order_status_log_repository
        self.product_repo = product_repository
        self.setting_repo = setting_repository

    def get_all(
        self,
        query=None,
        status=None,
        payment_status=None,
        payment_method=None,
        user_id=None,
        courier_id=None,
        has_courier=None,
        date_from=None,
        date_to=None,
        min_total=None,
        max_total=None,
        order_by="-created_at",
        page=1,
        per_page=20,
    ):
        qs = self.order_repo.get_all().select_related("user", "assigned_courier", "address")

        qs = self.order_repo.search(qs, query, SEARCH_FIELDS)

        filters = {
            "status": status,
            "payment_status": payment_status,
            "payment_method": payment_method,
            "user_id": user_id,
            "assigned_courier_id": courier_id,
        }
        qs = self.order_repo.apply_filters(qs, filters)

        if has_courier is True:
            qs = qs.filter(assigned_courier__isnull=False)
        elif has_courier is False:
            qs = qs.filter(assigned_courier__isnull=True)

        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        if min_total is not None:
            qs = qs.filter(total__gte=min_total)
        if max_total is not None:
            qs = qs.filter(total__lte=max_total)

        qs = self.order_repo.apply_ordering(qs, order_by, ORDER_FIELDS)

        return self.order_repo.paginate(qs, page, per_page)

    def get_by_id(self, order_id: int):
        order = (
            self.order_repo.get_all()
            .select_related("user", "assigned_courier", "address")
            .filter(pk=order_id)
            .first()
        )
        if not order:
            return None

        order._items = list(self.item_repo.get_by_order(order_id))
        order._status_log = list(self.log_repo.get_by_order(order_id).select_related("changed_by"))
        return order

    @transaction.atomic
    def update_status(self, order_id: int, new_status: str, admin_user, note: str = "") -> dict:
        if new_status not in VALID_STATUSES:
            raise ValidationError(f"Invalid status: {new_status}")

        order = Order.objects.select_for_update().filter(pk=order_id).first()
        if not order:
            raise NotFoundError("Order not found")

        old_status = order.status
        allowed = VALID_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Cannot transition from '{old_status}' to '{new_status}'. "
                f"Allowed: {', '.join(allowed) if allowed else 'none (terminal)'}"
            )

        # Auto-assign courier if moving to delivering/preparing and none assigned
        if new_status in ("preparing", "delivering") and not order.assigned_courier_id:
            courier = self._find_available_courier()
            if courier:
                self.order_repo.update(order, assigned_courier=courier)
                self.log_repo.log_transition(
                    order_id=order.id,
                    from_status=old_status,
                    to_status=old_status,
                    changed_by_id=admin_user.id,
                    note=f"Auto-assigned courier: {courier.first_name} (ID {courier.id})",
                )
            elif new_status == "delivering":
                raise ValidationError("No available couriers to assign")

        self.order_repo.update_status(order, new_status)

        self.log_repo.log_transition(
            order_id=order.id,
            from_status=old_status,
            to_status=new_status,
            changed_by_id=admin_user.id,
            note=note,
        )

        if new_status == "cancelled" and old_status in STOCK_DEDUCTED_STATUSES:
            self._restore_stock(order_id)

        # Grant referral reward on first delivered order
        if new_status == "delivered":
            try:
                from customer.services.v1.referral_service import CustomerReferralService
                from base.container import container
                ref_svc = container.resolve(CustomerReferralService)
                ref_svc.grant_reward_on_first_order(order.user_id)
            except Exception:
                pass  # Non-critical

        # Notify customer via Telegram
        try:
            order.refresh_from_db()
            from bot.notify import notify_customer_status_change
            notify_customer_status_change(order)
        except Exception:
            pass  # Non-critical

        return {"order_id": order.id, "status": new_status, "previous_status": old_status}

    @transaction.atomic
    def assign_courier(self, order_id: int, courier_id: int, admin_user) -> dict:
        order = Order.objects.select_for_update().filter(pk=order_id).first()
        if not order:
            raise NotFoundError("Order not found")

        if order.status in ("completed", "cancelled"):
            raise ValidationError("Cannot assign courier to a finished order")

        courier = User.objects.filter(
            pk=courier_id, role=User.Role.COURIER, is_active=True, deleted_at__isnull=True
        ).first()
        if not courier:
            raise ValidationError("Courier not found or inactive")

        old_courier_id = order.assigned_courier_id
        self.order_repo.update(order, assigned_courier=courier)

        self.log_repo.log_transition(
            order_id=order.id,
            from_status=order.status,
            to_status=order.status,
            changed_by_id=admin_user.id,
            note=f"Courier assigned: {courier.first_name} (ID {courier.id})"
            + (f", was: ID {old_courier_id}" if old_courier_id else ""),
        )

        return {"order_id": order.id, "courier_id": courier.id, "courier_name": courier.first_name}

    @transaction.atomic
    def unassign_courier(self, order_id: int, admin_user) -> dict:
        order = Order.objects.select_for_update().filter(pk=order_id).first()
        if not order:
            raise NotFoundError("Order not found")

        if order.status in ("delivering", "delivered", "completed", "cancelled"):
            raise ValidationError("Cannot unassign courier at this stage")

        if not order.assigned_courier_id:
            raise ValidationError("No courier assigned")

        old_id = order.assigned_courier_id
        self.order_repo.update(order, assigned_courier=None)

        self.log_repo.log_transition(
            order_id=order.id,
            from_status=order.status,
            to_status=order.status,
            changed_by_id=admin_user.id,
            note=f"Courier unassigned (was ID {old_id})",
        )

        return {"order_id": order.id, "message": "Courier unassigned"}

    def update_payment_status(self, order_id: int, payment_status: str, admin_user) -> dict:
        if payment_status not in VALID_PAYMENT_STATUSES:
            raise ValidationError(f"Invalid payment status: {payment_status}")

        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")

        old_ps = order.payment_status
        self.order_repo.update_payment_status(order, payment_status)

        self.log_repo.log_transition(
            order_id=order.id,
            from_status=order.status,
            to_status=order.status,
            changed_by_id=admin_user.id,
            note=f"Payment status: {old_ps} → {payment_status}",
        )

        return {"order_id": order.id, "payment_status": payment_status}

    def add_admin_note(self, order_id: int, note: str) -> dict:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")

        existing = order.admin_note
        updated = f"{existing}\n{note}".strip() if existing else note
        self.order_repo.update(order, admin_note=updated)

        return {"order_id": order.id, "admin_note": updated}

    @transaction.atomic
    def cancel(self, order_id: int, reason: str, admin_user) -> dict:
        order = Order.objects.select_for_update().filter(pk=order_id).first()
        if not order:
            raise NotFoundError("Order not found")

        if order.status in ("completed", "cancelled"):
            raise ValidationError(f"Cannot cancel a {order.status} order")

        old_status = order.status
        should_restore = old_status in STOCK_DEDUCTED_STATUSES

        self.order_repo.cancel(order, reason=reason)

        self.log_repo.log_transition(
            order_id=order.id,
            from_status=old_status,
            to_status="cancelled",
            changed_by_id=admin_user.id,
            note=f"Cancelled: {reason}" if reason else "Cancelled by admin",
        )

        if should_restore:
            self._restore_stock(order_id)

        return {"order_id": order.id, "status": "cancelled", "stock_restored": should_restore}

    @transaction.atomic
    def bulk_update_status(self, order_ids: list[int], new_status: str, admin_user, note: str = "") -> dict:
        if new_status not in VALID_STATUSES:
            raise ValidationError(f"Invalid status: {new_status}")

        orders = list(Order.objects.select_for_update().filter(pk__in=order_ids))
        if len(orders) != len(order_ids):
            found = {o.id for o in orders}
            missing = set(order_ids) - found
            raise ValidationError(f"Orders not found: {missing}")

        updated = []
        skipped = []
        for order in orders:
            allowed = VALID_TRANSITIONS.get(order.status, set())
            if new_status not in allowed:
                skipped.append({"id": order.id, "status": order.status, "reason": "invalid transition"})
                continue

            if new_status == "delivering" and not order.assigned_courier_id:
                skipped.append({"id": order.id, "status": order.status, "reason": "no courier assigned"})
                continue

            old_status = order.status
            self.order_repo.update_status(order, new_status)
            self.log_repo.log_transition(
                order_id=order.id,
                from_status=old_status,
                to_status=new_status,
                changed_by_id=admin_user.id,
                note=note or f"Bulk update to {new_status}",
            )
            updated.append(order.id)

        return {"updated": updated, "skipped": skipped}

    def get_min_order_total(self) -> Decimal:
        val = self.setting_repo.get_value("min_order_total", "0")
        return Decimal(str(val))

    def set_min_order_total(self, amount) -> dict:
        amount = Decimal(str(amount))
        if amount < 0:
            raise ValidationError("Minimum order total must be non-negative")
        self.setting_repo.set_value("min_order_total", str(amount), "string", "Minimum order total")
        return {"min_order_total": str(amount)}

    def _find_available_courier(self):
        """Find the courier with the fewest active deliveries."""
        from django.db.models import Count, Q

        active_statuses = ["confirmed", "preparing", "delivering"]
        couriers = (
            User.objects.filter(
                role=User.Role.COURIER,
                is_active=True,
                deleted_at__isnull=True,
            )
            .annotate(
                active_orders=Count(
                    "assigned_orders",
                    filter=Q(assigned_orders__status__in=active_statuses),
                )
            )
            .order_by("active_orders")
        )
        return couriers.first()

    def stats(self, date_from=None, date_to=None) -> dict:
        qs = self.order_repo.get_all()

        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        total = qs.count()
        by_status = dict(
            qs.values_list("status").annotate(c=Count("id")).values_list("status", "c")
        )

        completed = qs.filter(status__in=["completed", "delivered"])
        revenue_agg = completed.aggregate(
            total_revenue=Sum("total"),
            avg_order=Avg("total"),
            min_order=Min("total"),
            max_order=Max("total"),
        )

        by_payment_method = dict(
            qs.exclude(payment_method__isnull=True)
            .values_list("payment_method")
            .annotate(c=Count("id"))
            .values_list("payment_method", "c")
        )

        by_payment_status = dict(
            qs.values_list("payment_status").annotate(c=Count("id")).values_list("payment_status", "c")
        )

        orders_by_day = list(
            qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"), revenue=Sum("total"))
            .order_by("-day")[:30]
        )

        cancellation_count = qs.filter(status="cancelled").count()
        cancellation_rate = round(cancellation_count / total * 100, 1) if total > 0 else 0

        fulfilled = qs.filter(
            confirmed_at__isnull=False, delivered_at__isnull=False
        ).annotate(
            fulfillment_time=ExpressionWrapper(
                F("delivered_at") - F("confirmed_at"), output_field=DurationField()
            )
        )
        avg_fulfillment = fulfilled.aggregate(avg=Avg("fulfillment_time"))["avg"]
        avg_fulfillment_minutes = round(avg_fulfillment.total_seconds() / 60) if avg_fulfillment else None

        courier_stats = list(
            qs.filter(assigned_courier__isnull=False)
            .values("assigned_courier_id", "assigned_courier__first_name", "assigned_courier__last_name")
            .annotate(
                order_count=Count("id"),
                delivered_count=Count("id", filter=Q(status__in=["delivered", "completed"])),
            )
            .order_by("-order_count")[:10]
        )

        peak_hours = list(
            qs.annotate(hour=ExtractHour("created_at"))
            .values("hour")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        pending_count = qs.filter(status="pending").count()
        unassigned = qs.filter(
            status__in=["confirmed", "preparing"],
            assigned_courier__isnull=True,
        ).count()

        return {
            "total": total,
            "by_status": by_status,
            "revenue": {
                "total": str(revenue_agg["total_revenue"] or 0),
                "avg": str(round(revenue_agg["avg_order"] or 0, 2)),
                "min": str(revenue_agg["min_order"] or 0),
                "max": str(revenue_agg["max_order"] or 0),
            },
            "by_payment_method": by_payment_method,
            "by_payment_status": by_payment_status,
            "cancellation_rate": cancellation_rate,
            "avg_fulfillment_minutes": avg_fulfillment_minutes,
            "pending_count": pending_count,
            "unassigned_orders": unassigned,
            "orders_by_day": [
                {
                    "date": d["day"].isoformat() if d["day"] else None,
                    "count": d["count"],
                    "revenue": str(d["revenue"] or 0),
                }
                for d in orders_by_day
            ],
            "courier_performance": [
                {
                    "id": c["assigned_courier_id"],
                    "name": f"{c['assigned_courier__first_name']} {c['assigned_courier__last_name']}",
                    "total_orders": c["order_count"],
                    "delivered": c["delivered_count"],
                }
                for c in courier_stats
            ],
            "peak_hours": [
                {"hour": h["hour"], "count": h["count"]}
                for h in peak_hours
            ],
        }

    def _restore_stock(self, order_id: int):
        items = self.item_repo.get_by_order(order_id)
        for item in items:
            if item.product_id:
                self.product_repo.increase_stock(item.product_id, item.quantity)
