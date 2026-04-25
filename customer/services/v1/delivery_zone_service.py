from decimal import Decimal

from base.interfaces.delivery import IDeliveryZoneRepository


class CustomerDeliveryZoneService:
    def __init__(self, delivery_zone_repository: IDeliveryZoneRepository):
        self.zone_repo = delivery_zone_repository

    def check_delivery(self, latitude: Decimal, longitude: Decimal) -> dict:
        zones = list(self.zone_repo.get_all().filter(is_active=True).order_by("sort_order"))

        for zone in zones:
            polygon = zone.polygon
            if not polygon:
                continue

            coords = self._extract_coords(polygon)
            if coords and self._point_in_polygon(latitude, longitude, coords):
                return {
                    "available": True,
                    "zone_id": zone.id,
                    "zone_name": zone.name,
                    "delivery_fee": str(zone.delivery_fee),
                    "min_order": str(zone.min_order),
                    "estimated_minutes": zone.estimated_minutes,
                }

        return {"available": False}

    def get_zone_for_point(self, latitude: Decimal, longitude: Decimal):
        zones = list(self.zone_repo.get_all().filter(is_active=True).order_by("sort_order"))
        for zone in zones:
            polygon = zone.polygon
            if not polygon:
                continue
            coords = self._extract_coords(polygon)
            if coords and self._point_in_polygon(latitude, longitude, coords):
                return zone
        return None

    @staticmethod
    def _extract_coords(polygon):
        if isinstance(polygon, dict):
            geo_type = polygon.get("type", "")
            if geo_type == "Polygon":
                coords = polygon.get("coordinates", [])
                return coords[0] if coords else None
            elif geo_type == "Feature":
                geom = polygon.get("geometry", {})
                coords = geom.get("coordinates", [])
                return coords[0] if coords else None
        elif isinstance(polygon, list):
            return polygon if polygon else None
        return None

    @staticmethod
    def _point_in_polygon(lat, lng, coords):
        lat = float(lat)
        lng = float(lng)
        n = len(coords)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = float(coords[i][0]), float(coords[i][1])
            xj, yj = float(coords[j][0]), float(coords[j][1])
            if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside
