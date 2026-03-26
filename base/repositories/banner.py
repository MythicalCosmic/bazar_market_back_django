from django.db.models import QuerySet, Q
from django.utils import timezone

from base.models import Banner
from base.repositories.base import BaseRepository


class BannerRepository(BaseRepository[Banner]):
    model = Banner

    def get_active(self) -> QuerySet[Banner]:
        return self.get_queryset().filter(is_active=True)

    def get_current(self) -> QuerySet[Banner]:
        now = timezone.now()
        return self.get_active().filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        )

    def deactivate(self, banner: Banner) -> Banner:
        return self.update(banner, is_active=False)

    def activate(self, banner: Banner) -> Banner:
        return self.update(banner, is_active=True)

    def reorder(self, banner_ids: list[int]) -> None:
        for index, pk in enumerate(banner_ids):
            self.model.objects.filter(pk=pk).update(sort_order=index)
