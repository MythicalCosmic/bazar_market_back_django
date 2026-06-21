"""Serializers that produce the EXACT shapes the Market courier app consumes
(see the app's src/data.js). Money is integer so'm; times the app renders are
short "HH:MM" strings; history `date` is ISO (the app formats it).

Everything here is wrapped by base.responses.success(...) at the view layer, so
the app reads these dicts from `response.data`.
"""
import math
from decimal import Decimal, InvalidOperation

from django.utils import timezone

COMMISSION_RATE = Decimal("0.01")          # 1% commission on order value
_AVG_SPEED_KMH = 20                         # for a coarse ETA from distance


def money(value) -> int:
    """Decimal/None -> integer so'm."""
    if value is None:
        return 0
    try:
        return int(Decimal(value))
    except (TypeError, ValueError, InvalidOperation):
        return 0


def _qty(value):
    """Decimal quantity -> int when whole, else float (e.g. 1.5 kg)."""
    try:
        d = Decimal(value)
    except (TypeError, ValueError, InvalidOperation):
        return 0
    return int(d) if d == d.to_integral_value() else float(d)


def _customer_name(order) -> str:
    u = order.user
    name = (u.first_name or "").strip()
    if u.last_name:
        name = f"{name} {u.last_name}".strip()
    return name


def _district(order) -> str:
    addr = getattr(order, "address", None)
    if addr and getattr(addr, "label", ""):
        return addr.label
    return ""


def _coords(lat, lng):
    if lat is None or lng is None:
        return None
    try:
        return {"lat": float(lat), "lng": float(lng)}
    except (TypeError, ValueError):
        return None


def _haversine_km(a, b):
    if not a or not b:
        return None
    r = 6371.0
    dlat = math.radians(b["lat"] - a["lat"])
    dlng = math.radians(b["lng"] - a["lng"])
    h = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a["lat"])) * math.cos(math.radians(b["lat"]))
         * math.sin(dlng / 2) ** 2)
    return round(r * 2 * math.asin(min(1.0, math.sqrt(h))), 1)


def _distance_eta(origin, dest):
    km = _haversine_km(origin, dest)
    if km is None:
        return None, None
    eta = max(1, round(km / _AVG_SPEED_KMH * 60))
    return km, eta


# --------------------------------------------------------------------------- #
# courier identity / profile
# --------------------------------------------------------------------------- #
def courier_public(user, profile) -> dict:
    return {
        "id": f"MK-{user.id:04d}",
        "name": (user.first_name or "").strip(),
        "phone": user.phone or "",
        "rating": float(profile.rating) if profile else 5.0,
        "vehicle": {
            "type": profile.vehicle_type if profile else "motorcycle",
            "plate": profile.vehicle_plate if profile else "",
        },
        "online": bool(profile.is_online) if profile else False,
    }


def courier_me(user, profile) -> dict:
    data = courier_public(user, profile)
    prefs = (profile.prefs if profile else {}) or {}
    data["prefs"] = {
        "push": prefs.get("push", True),
        "sound": prefs.get("sound", True),
        "accent": prefs.get("accent", "indigo"),
        "lang": user.language,
        "dark": prefs.get("dark", True),
    }
    return data


# --------------------------------------------------------------------------- #
# orders
# --------------------------------------------------------------------------- #
def active_order(order, state, origin=None) -> dict:
    dest = _coords(order.delivery_lat, order.delivery_lng)
    distance_km, eta_min = _distance_eta(origin, dest)
    items = getattr(order, "_items", [])
    return {
        "id": order.order_number,
        "customer": _customer_name(order),
        "phone": order.user.phone or "",
        "address": order.delivery_address_text or "",
        "district": _district(order),
        "distanceKm": distance_km,
        "etaMin": eta_min,
        "payment": order.payment_method or "cash",
        "status": state.status if state else "new",
        "deliveryFee": money(order.delivery_fee),
        "placedAt": timezone.localtime(order.created_at).strftime("%H:%M"),
        "origin": origin,
        "dest": dest,
        "items": [
            {
                "name": it.product_name,
                "qty": _qty(it.quantity),
                "price": money(it.unit_price),
            }
            for it in items
        ],
    }


def history_order(order) -> dict:
    delivered = order.status in ("delivered", "completed")
    total = money(order.total)
    earned = 0
    if delivered:
        earned = money(order.delivery_fee) + int(Decimal(total) * COMMISSION_RATE)
    return {
        "id": order.order_number,
        "customer": _customer_name(order),
        "district": _district(order),
        "status": "delivered" if delivered else "cancelled",
        "total": total,
        "deliveryFee": money(order.delivery_fee),
        "items": getattr(order, "_item_count", 0),
        "date": order.created_at.isoformat(),
        "earned": earned,
    }
