from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count

from base.interfaces.delivery import IDeliveryZoneRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.delivery_zone import CreateDeliveryZoneDTO, UpdateDeliveryZoneDTO


class DeliveryZoneService:
    def __init__(self, delivery_zone_repository: IDeliveryZoneRepository):
        self.zone_repo = delivery_zone_repository

    def get_all(self, is_active=None, order_by="sort_order", page=1, per_page=20):
        qs = self.zone_repo.get_all()
        qs = self.zone_repo.apply_filters(qs, {"is_active": is_active})
        qs = self.zone_repo.apply_ordering(qs, order_by, {"sort_order", "name", "delivery_fee", "created_at"})
        return self.zone_repo.paginate(qs, page, per_page)

    def get_by_id(self, zone_id: int):
        return self.zone_repo.get_by_id(zone_id)

    def create_zone(self, dto: CreateDeliveryZoneDTO) -> dict:
        try:
            fee = Decimal(dto.delivery_fee)
            if fee < 0:
                raise ValidationError("Delivery fee must be non-negative")
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid delivery_fee")

        try:
            min_order = Decimal(dto.min_order)
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid min_order")

        if not isinstance(dto.polygon, (dict, list)):
            raise ValidationError("polygon must be a GeoJSON object or coordinate array")

        zone = self.zone_repo.create(
            name=dto.name,
            polygon=dto.polygon,
            delivery_fee=fee,
            min_order=min_order,
            estimated_minutes=dto.estimated_minutes,
            is_active=dto.is_active,
            sort_order=dto.sort_order,
        )
        return {"id": zone.id, "name": zone.name}

    def update_zone(self, zone_id: int, dto: UpdateDeliveryZoneDTO) -> dict:
        zone = self.zone_repo.get_by_id(zone_id)
        if not zone:
            raise NotFoundError("Delivery zone not found")

        data = dto.to_dict()

        for decimal_field in ("delivery_fee", "min_order"):
            if decimal_field in data and data[decimal_field] is not None:
                try:
                    data[decimal_field] = Decimal(str(data[decimal_field]))
                except (InvalidOperation, ValueError):
                    raise ValidationError(f"Invalid {decimal_field}")

        if "delivery_fee" in data and data["delivery_fee"] < 0:
            raise ValidationError("Delivery fee must be non-negative")

        if data:
            self.zone_repo.update(zone, **data)

        return {"id": zone.id, "name": zone.name}

    def delete_zone(self, zone_id: int) -> dict:
        zone = self.zone_repo.get_by_id(zone_id)
        if not zone:
            raise NotFoundError("Delivery zone not found")
        self.zone_repo.delete(zone)
        return {"message": "Delivery zone deleted"}

    @transaction.atomic
    def reorder(self, zone_ids: list[int]) -> dict:
        existing = set(
            self.zone_repo.get_all()
            .filter(pk__in=zone_ids)
            .values_list("pk", flat=True)
        )
        missing = set(zone_ids) - existing
        if missing:
            raise ValidationError(f"Zones not found: {missing}")

        self.zone_repo.reorder(zone_ids)
        return {"message": "Zones reordered"}

    def activate(self, zone_id: int) -> dict:
        zone = self.zone_repo.get_by_id(zone_id)
        if not zone:
            raise NotFoundError("Delivery zone not found")
        self.zone_repo.activate(zone)
        return {"message": "Zone activated"}

    def deactivate(self, zone_id: int) -> dict:
        zone = self.zone_repo.get_by_id(zone_id)
        if not zone:
            raise NotFoundError("Delivery zone not found")
        self.zone_repo.deactivate(zone)
        return {"message": "Zone deactivated"}

    def stats(self) -> dict:
        qs = self.zone_repo.get_all()
        total = qs.count()
        active = qs.filter(is_active=True).count()

        from django.db.models import Avg, Min, Max
        fee_agg = qs.filter(is_active=True).aggregate(
            avg_fee=Avg("delivery_fee"),
            min_fee=Min("delivery_fee"),
            max_fee=Max("delivery_fee"),
            avg_min_order=Avg("min_order"),
            avg_est_minutes=Avg("estimated_minutes"),
        )

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "fee_range": {
                "avg": str(round(fee_agg["avg_fee"] or 0, 2)),
                "min": str(fee_agg["min_fee"] or 0),
                "max": str(fee_agg["max_fee"] or 0),
            },
            "avg_min_order": str(round(fee_agg["avg_min_order"] or 0, 2)),
            "avg_estimated_minutes": round(fee_agg["avg_est_minutes"] or 0),
        }
