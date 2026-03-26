from abc import abstractmethod

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import DeliveryZone


class IDeliveryZoneRepository(IBaseRepository[DeliveryZone]):

    @abstractmethod
    def get_active(self) -> QuerySet[DeliveryZone]: ...

    @abstractmethod
    def deactivate(self, zone: DeliveryZone) -> DeliveryZone: ...

    @abstractmethod
    def activate(self, zone: DeliveryZone) -> DeliveryZone: ...

    @abstractmethod
    def reorder(self, zone_ids: list[int]) -> None: ...
