from decimal import Decimal

from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

from base.interfaces.payment import IPaymentRepository
from base.interfaces.order import IOrderRepository
from base.exceptions import NotFoundError, ValidationError


VALID_TRANSITIONS = {
    "pending": {"processing", "completed", "failed"},
    "processing": {"completed", "failed"},
    "completed": {"refunded"},
    "failed": set(),
    "refunded": set(),
}


class PaymentService:
    def __init__(
        self,
        payment_repository: IPaymentRepository,
        order_repository: IOrderRepository,
    ):
        self.payment_repo = payment_repository
        self.order_repo = order_repository

    def get_all(
        self,
        query=None,
        status=None,
        method=None,
        order_id=None,
        date_from=None,
        date_to=None,
        min_amount=None,
        max_amount=None,
        order_by="-created_at",
        page=1,
        per_page=20,
    ):
        qs = self.payment_repo.get_all().select_related("order", "order__user")

        if query:
            qs = self.payment_repo.search(
                qs, query, ["order__order_number", "order__user__phone"]
            )
        if status:
            qs = qs.filter(status=status)
        if method:
            qs = qs.filter(method=method)
        if order_id:
            qs = qs.filter(order_id=order_id)
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        if min_amount is not None:
            qs = qs.filter(amount__gte=Decimal(str(min_amount)))
        if max_amount is not None:
            qs = qs.filter(amount__lte=Decimal(str(max_amount)))

        qs = self.payment_repo.apply_ordering(
            qs, order_by, {"created_at", "amount", "status", "method", "paid_at"}
        )
        return self.payment_repo.paginate(qs, page, per_page)

    def get_by_id(self, payment_id: int):
        return (
            self.payment_repo.get_all()
            .select_related("order", "order__user")
            .filter(pk=payment_id)
            .first()
        )

    def update_status(self, payment_id: int, new_status: str) -> dict:
        payment = self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError("Payment not found")

        if new_status not in VALID_TRANSITIONS.get(payment.status, set()):
            raise ValidationError(
                f"Cannot transition from '{payment.status}' to '{new_status}'"
            )

        kwargs = {"status": new_status}
        if new_status == "completed":
            kwargs["paid_at"] = timezone.now()

        self.payment_repo.update(payment, **kwargs)

        if new_status == "completed":
            self.order_repo.bulk_update(
                self.order_repo.get_all().filter(pk=payment.order_id),
                payment_status="paid",
            )
        elif new_status == "refunded":
            self.order_repo.bulk_update(
                self.order_repo.get_all().filter(pk=payment.order_id),
                payment_status="refunded",
            )

        return {"message": f"Payment status updated to {new_status}"}

    def refund(self, payment_id: int, reason: str = "") -> dict:
        payment = self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError("Payment not found")
        if payment.status != "completed":
            raise ValidationError("Only completed payments can be refunded")

        self.payment_repo.mark_refunded(payment)

        self.order_repo.bulk_update(
            self.order_repo.get_all().filter(pk=payment.order_id),
            payment_status="refunded",
        )

        return {"message": "Payment refunded"}

    def get_by_order(self, order_id: int):
        return list(
            self.payment_repo.get_by_order(order_id)
            .select_related("order")
            .order_by("-created_at")
        )

    def stats(self, date_from=None, date_to=None) -> dict:
        qs = self.payment_repo.get_all()

        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        total = qs.count()
        by_status = dict(
            qs.values_list("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )
        by_method = dict(
            qs.values_list("method")
            .annotate(c=Count("id"))
            .values_list("method", "c")
        )

        completed = qs.filter(status="completed")
        revenue = completed.aggregate(
            total=Sum("amount"),
            avg=Avg("amount"),
        )

        refunded = qs.filter(status="refunded")
        refund_agg = refunded.aggregate(
            total=Sum("amount"),
            count=Count("id"),
        )

        pending_amount = qs.filter(status="pending").aggregate(total=Sum("amount"))

        return {
            "total": total,
            "by_status": by_status,
            "by_method": by_method,
            "revenue": str(revenue["total"] or 0),
            "avg_payment": str(round(revenue["avg"] or 0, 2)),
            "refunded_amount": str(refund_agg["total"] or 0),
            "refund_count": refund_agg["count"],
            "pending_amount": str(pending_amount["total"] or 0),
            "completed_count": by_status.get("completed", 0),
            "failed_count": by_status.get("failed", 0),
        }
