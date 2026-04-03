from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from base.interfaces.banner import IBannerRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.banner import CreateBannerDTO, UpdateBannerDTO
from base.models import Banner


VALID_LINK_TYPES = {c[0] for c in Banner.LinkType.choices}


def _parse_dt(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    return datetime.fromisoformat(val)


class BannerService:
    def __init__(self, banner_repository: IBannerRepository):
        self.banner_repo = banner_repository

    def get_all(self, is_active=None, scheduled=None, order_by="sort_order", page=1, per_page=20):
        qs = self.banner_repo.get_all()
        qs = self.banner_repo.apply_filters(qs, {"is_active": is_active})

        now = timezone.now()
        if scheduled == "current":
            qs = qs.filter(
                Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                Q(expires_at__isnull=True) | Q(expires_at__gte=now),
            )
        elif scheduled == "upcoming":
            qs = qs.filter(starts_at__gt=now)
        elif scheduled == "expired":
            qs = qs.filter(expires_at__lt=now)

        qs = self.banner_repo.apply_ordering(qs, order_by, {"sort_order", "created_at"})
        return self.banner_repo.paginate(qs, page, per_page)

    def get_by_id(self, banner_id: int):
        return self.banner_repo.get_by_id(banner_id)

    def create_banner(self, dto: CreateBannerDTO) -> dict:
        if dto.link_type not in VALID_LINK_TYPES:
            raise ValidationError(f"Invalid link_type. Must be one of: {', '.join(VALID_LINK_TYPES)}")

        banner = self.banner_repo.create(
            title=dto.title,
            image=dto.image,
            link_type=dto.link_type,
            link_value=dto.link_value,
            sort_order=dto.sort_order,
            starts_at=_parse_dt(dto.starts_at),
            expires_at=_parse_dt(dto.expires_at),
            is_active=dto.is_active,
        )
        return {"id": banner.id, "title": banner.title}

    def update_banner(self, banner_id: int, dto: UpdateBannerDTO) -> dict:
        banner = self.banner_repo.get_by_id(banner_id)
        if not banner:
            raise NotFoundError("Banner not found")

        data = dto.to_dict()

        if "link_type" in data and data["link_type"] not in VALID_LINK_TYPES:
            raise ValidationError(f"Invalid link_type")

        for dt_field in ("starts_at", "expires_at"):
            if dt_field in data:
                data[dt_field] = _parse_dt(data[dt_field])

        if data:
            self.banner_repo.update(banner, **data)

        return {"id": banner.id, "title": banner.title}

    def delete_banner(self, banner_id: int) -> dict:
        banner = self.banner_repo.get_by_id(banner_id)
        if not banner:
            raise NotFoundError("Banner not found")
        self.banner_repo.delete(banner)
        return {"message": "Banner deleted"}

    @transaction.atomic
    def reorder(self, banner_ids: list[int]) -> dict:
        existing = set(
            self.banner_repo.get_all()
            .filter(pk__in=banner_ids)
            .values_list("pk", flat=True)
        )
        missing = set(banner_ids) - existing
        if missing:
            raise ValidationError(f"Banners not found: {missing}")

        self.banner_repo.reorder(banner_ids)
        return {"message": "Banners reordered"}

    def activate(self, banner_id: int) -> dict:
        banner = self.banner_repo.get_by_id(banner_id)
        if not banner:
            raise NotFoundError("Banner not found")
        self.banner_repo.activate(banner)
        return {"message": "Banner activated"}

    def deactivate(self, banner_id: int) -> dict:
        banner = self.banner_repo.get_by_id(banner_id)
        if not banner:
            raise NotFoundError("Banner not found")
        self.banner_repo.deactivate(banner)
        return {"message": "Banner deactivated"}

    def stats(self) -> dict:
        qs = self.banner_repo.get_all()
        now = timezone.now()
        total = qs.count()
        active = qs.filter(is_active=True).count()
        current = qs.filter(
            is_active=True,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        ).count()
        upcoming = qs.filter(starts_at__gt=now).count()
        expired = qs.filter(expires_at__lt=now).count()
        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "currently_showing": current,
            "upcoming": upcoming,
            "expired": expired,
        }
