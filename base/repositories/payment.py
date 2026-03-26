from typing import Optional

from django.db.models import QuerySet
from django.utils import timezone

from base.models import Payment
from base.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    model = Payment

    def get_by_uuid(self, uuid) -> Optional[Payment]:
        return self.get_queryset().filter(uuid=uuid).first()

    def get_by_order(self, order_id: int) -> QuerySet[Payment]:
        return self.get_queryset().filter(order_id=order_id)

    def get_by_external_id(self, external_id: str) -> Optional[Payment]:
        return self.get_queryset().filter(external_id=external_id).first()

    def get_by_status(self, status: str) -> QuerySet[Payment]:
        return self.get_queryset().filter(status=status)

    def get_by_method(self, method: str) -> QuerySet[Payment]:
        return self.get_queryset().filter(method=method)

    def get_pending(self) -> QuerySet[Payment]:
        return self.get_by_status(Payment.Status.PENDING)

    def mark_completed(self, payment: Payment, external_id: str = "") -> Payment:
        kwargs: dict = {
            "status": Payment.Status.COMPLETED,
            "paid_at": timezone.now(),
        }
        if external_id:
            kwargs["external_id"] = external_id
        return self.update(payment, **kwargs)

    def mark_failed(self, payment: Payment) -> Payment:
        return self.update(payment, status=Payment.Status.FAILED)

    def mark_refunded(self, payment: Payment) -> Payment:
        return self.update(payment, status=Payment.Status.REFUNDED)

    def update_provider_data(self, payment: Payment, data: dict) -> Payment:
        return self.update(payment, provider_data=data)
