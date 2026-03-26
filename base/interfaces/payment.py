from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import Payment


class IPaymentRepository(IBaseRepository[Payment]):

    @abstractmethod
    def get_by_uuid(self, uuid) -> Optional[Payment]: ...

    @abstractmethod
    def get_by_order(self, order_id: int) -> QuerySet[Payment]: ...

    @abstractmethod
    def get_by_external_id(self, external_id: str) -> Optional[Payment]: ...

    @abstractmethod
    def get_by_status(self, status: str) -> QuerySet[Payment]: ...

    @abstractmethod
    def get_by_method(self, method: str) -> QuerySet[Payment]: ...

    @abstractmethod
    def get_pending(self) -> QuerySet[Payment]: ...

    @abstractmethod
    def mark_completed(
        self, payment: Payment, external_id: str = ""
    ) -> Payment: ...

    @abstractmethod
    def mark_failed(self, payment: Payment) -> Payment: ...

    @abstractmethod
    def mark_refunded(self, payment: Payment) -> Payment: ...

    @abstractmethod
    def update_provider_data(self, payment: Payment, data: dict) -> Payment: ...
