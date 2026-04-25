from django.db.models import Q
from django.utils import timezone

from base.interfaces.banner import IBannerRepository


class CustomerBannerService:
    def __init__(self, banner_repository: IBannerRepository):
        self.banner_repo = banner_repository

    def get_active_banners(self) -> list:
        now = timezone.now()
        return list(
            self.banner_repo.get_all()
            .filter(is_active=True)
            .filter(
                Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                Q(expires_at__isnull=True) | Q(expires_at__gte=now),
            )
            .order_by("sort_order")
        )
