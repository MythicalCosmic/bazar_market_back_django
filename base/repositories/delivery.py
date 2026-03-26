from django.db.models import QuerySet

from base.models import DeliveryZone
from base.repositories.base import BaseRepository


class DeliveryZoneRepository(BaseRepository[DeliveryZone]):
    model = DeliveryZone

    def get_active(self) -> QuerySet[DeliveryZone]:
        return self.get_queryset().filter(is_active=True)

    def deactivate(self, zone: DeliveryZone) -> DeliveryZone:
        return self.update(zone, is_active=False)

    def activate(self, zone: DeliveryZone) -> DeliveryZone:
        return self.update(zone, is_active=True)

    def reorder(self, zone_ids: list[int]) -> None:
        for index, pk in enumerate(zone_ids):
            self.model.objects.filter(pk=pk).update(sort_order=index)
