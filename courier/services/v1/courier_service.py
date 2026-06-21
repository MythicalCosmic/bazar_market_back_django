"""Courier domain logic: profile/presence, dashboard, assigned orders, the
status flow, history and push-device registration.

An order is "the courier's" when ``Order.assigned_courier`` points at them
(admins assign — left untouched). The courier's status projection lives in
``CourierOrderState``; advancing to onway/delivered also moves the shared
``Order.status`` so the rest of the system (admin, customer) stays in sync.
Money in/out of here is integer so'm (serializers coerce).
"""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from base.exceptions import NotFoundError, ValidationError
from base.interfaces.setting import ISettingRepository
from base.models import Order, OrderItem, OrderStatusLog, User

from courier.models import CourierProfile, CourierOrderState, PushDevice
from courier.serializers import COMMISSION_RATE

# Orders no longer "active" for the courier once they reach these.
_TERMINAL = ("delivered", "completed", "cancelled")
_STEP_TS = {
    "accepted": "accepted_at",
    "picked": "picked_at",
    "onway": "onway_at",
    "delivered": "delivered_at",
}


def _today_start():
    now = timezone.localtime()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _period_start(period: str):
    now = timezone.now()
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    if period == "all":
        return None
    return _today_start()           # default: today


class CourierService:
    def __init__(self, setting_repository: ISettingRepository):
        self.setting_repo = setting_repository

    # ── profile / presence ────────────────────────────────────
    def get_profile(self, user) -> CourierProfile:
        profile, _ = CourierProfile.objects.get_or_create(user=user)
        return profile

    def set_online(self, user, online: bool) -> CourierProfile:
        profile = self.get_profile(user)
        profile.is_online = bool(online)
        profile.save(update_fields=["is_online", "updated_at"])
        return profile

    def update_prefs(self, user, data: dict) -> CourierProfile:
        profile = self.get_profile(user)
        prefs = dict(profile.prefs or {})
        for key in ("push", "sound", "accent", "dark"):
            if key in data:
                prefs[key] = data[key]
        profile.prefs = prefs
        profile.save(update_fields=["prefs", "updated_at"])
        lang = data.get("lang")
        if lang and lang in dict(User.Language.choices) and user.language != lang:
            user.language = lang
            user.save(update_fields=["language", "updated_at"])
        return profile

    # ── store origin (for distance/ETA) ───────────────────────
    def store_origin(self):
        lat = self.setting_repo.get_value("store_lat", None)
        lng = self.setting_repo.get_value("store_lng", None)
        if lat in (None, "") or lng in (None, ""):
            return None
        try:
            return {"lat": float(lat), "lng": float(lng)}
        except (TypeError, ValueError):
            return None

    # ── orders: active ────────────────────────────────────────
    def active_orders(self, user):
        orders = list(
            Order.objects.filter(assigned_courier=user)
            .exclude(status__in=_TERMINAL)
            .select_related("user", "address")
            .order_by("-created_at")
        )
        self._attach_items(orders)
        states = self._states_map([o.id for o in orders])
        return orders, states, self.store_origin()

    def get_order(self, user, ref: str):
        order = (
            self._owned_qs(user)
            .select_related("user", "address")
            .filter(self._ref_q(ref))
            .first()
        )
        if not order:
            return None, None, None
        self._attach_items([order])
        state = CourierOrderState.objects.filter(order=order).first()
        return order, state, self.store_origin()

    # ── orders: advance status ────────────────────────────────
    @transaction.atomic
    def advance_status(self, user, ref: str, target: str):
        order = (
            self._owned_qs(user)
            .select_for_update()
            .filter(self._ref_q(ref))
            .first()
        )
        if not order:
            raise NotFoundError("Order not found")

        target = (target or "").strip().lower()
        if target not in CourierOrderState.FLOW:
            raise ValidationError(f"Invalid status '{target}'")

        state, _ = CourierOrderState.objects.select_for_update().get_or_create(
            order=order, defaults={"courier": user, "status": CourierOrderState.Status.NEW}
        )
        if not state.can_advance_to(target):
            raise ValidationError(f"Cannot move from '{state.status}' to '{target}'")

        now = timezone.now()
        state.status = target
        fields = ["status", "updated_at"]
        ts_field = _STEP_TS.get(target)
        if ts_field:
            setattr(state, ts_field, now)
            fields.append(ts_field)
        state.save(update_fields=fields)

        # Mirror the meaningful transitions onto the shared order lifecycle.
        if target == "onway" and order.status not in ("delivering", "delivered", "completed"):
            self._move_order(order, Order.Status.DELIVERING, "delivering_at", now, user)
        elif target == "delivered" and order.status not in ("delivered", "completed"):
            self._move_order(order, Order.Status.DELIVERED, "delivered_at", now, user)

        return order, state, now

    def advance_next(self, user, ref: str):
        """Compute the next status from the current state and advance to it."""
        order = self._owned_qs(user).filter(self._ref_q(ref)).first()
        if not order:
            raise NotFoundError("Order not found")
        state = CourierOrderState.objects.filter(order=order).first()
        current = state.status if state else CourierOrderState.Status.NEW
        try:
            nxt = CourierOrderState.FLOW[CourierOrderState.FLOW.index(current) + 1]
        except (ValueError, IndexError):
            raise ValidationError("Order is already at its final status")
        return self.advance_status(user, ref, nxt)

    def _move_order(self, order, new_status, ts_field, now, user):
        prev = order.status
        order.status = new_status
        setattr(order, ts_field, now)
        order.save(update_fields=["status", ts_field, "updated_at"])
        OrderStatusLog.objects.create(
            order=order, from_status=prev, to_status=new_status,
            changed_by=user, note="Courier app",
        )

    # ── dashboard ─────────────────────────────────────────────
    def dashboard_stats(self, user, date: str = "today") -> dict:
        start = _today_start()
        base = Order.objects.filter(assigned_courier=user)
        orders_today = base.filter(created_at__gte=start).count()

        delivered_qs = base.filter(
            status__in=("delivered", "completed"), delivered_at__gte=start
        )
        delivered = delivered_qs.count()
        agg = delivered_qs.aggregate(value=Sum("total"), fees=Sum("delivery_fee"))
        orders_value = int(agg["value"] or 0)
        delivery_earnings = int(agg["fees"] or 0)
        commission = int(Decimal(orders_value) * COMMISSION_RATE)
        return {
            "ordersToday": orders_today,
            "delivered": delivered,
            "remaining": max(0, orders_today - delivered),
            "ordersValue": orders_value,
            "deliveryEarnings": delivery_earnings,
            "commission": commission,
            "totalEarned": commission + delivery_earnings,
        }

    # ── history ───────────────────────────────────────────────
    def history(self, user, period="today", status="all", q="", page=1, page_size=20):
        qs = (
            Order.objects.filter(
                assigned_courier=user,
                status__in=("delivered", "completed", "cancelled"),
            )
            .select_related("user", "address")
        )
        start = _period_start(period)
        if start is not None:
            qs = qs.filter(created_at__gte=start)
        if status == "delivered":
            qs = qs.filter(status__in=("delivered", "completed"))
        elif status == "cancelled":
            qs = qs.filter(status="cancelled")
        if q:
            qs = qs.filter(
                Q(order_number__icontains=q)
                | Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
            )
        qs = qs.order_by("-created_at")

        delivered_q = Q(status__in=("delivered", "completed"))
        summary_agg = qs.aggregate(
            delivered_count=Count("id", filter=delivered_q),
            total_count=Count("id"),
            fees=Sum("delivery_fee", filter=delivered_q),
            value=Sum("total", filter=delivered_q),
        )
        earned = int(summary_agg["fees"] or 0) + int(
            Decimal(int(summary_agg["value"] or 0)) * COMMISSION_RATE
        )
        total = summary_agg["total_count"] or 0

        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        items = list(qs.annotate(_item_count=Count("items"))[offset:offset + page_size])

        return {
            "summary": {
                "earned": earned,
                "deliveredCount": summary_agg["delivered_count"] or 0,
                "totalCount": total,
            },
            "page": page,
            "pageSize": page_size,
            "total": total,
            "orders": items,
        }

    # ── push devices ──────────────────────────────────────────
    def register_device(self, user, token: str, platform: str = "") -> PushDevice:
        token = (token or "").strip()
        if not token:
            raise ValidationError("token is required")
        device, _ = PushDevice.objects.update_or_create(
            token=token, defaults={"user": user, "platform": (platform or "")[:16]}
        )
        return device

    def unregister_device(self, user, token: str) -> int:
        count, _ = PushDevice.objects.filter(user=user, token=token).delete()
        return count

    # ── helpers ───────────────────────────────────────────────
    def _owned_qs(self, user):
        return Order.objects.filter(assigned_courier=user)

    @staticmethod
    def _ref_q(ref: str) -> Q:
        ref = (ref or "").strip()
        q = Q(order_number=ref)
        if ref.isdigit():
            q |= Q(pk=int(ref))
        return q

    @staticmethod
    def _attach_items(orders):
        ids = [o.id for o in orders]
        by_order = defaultdict(list)
        for it in OrderItem.objects.filter(order_id__in=ids):
            by_order[it.order_id].append(it)
        for o in orders:
            o._items = by_order.get(o.id, [])

    @staticmethod
    def _states_map(order_ids):
        return {
            s.order_id: s
            for s in CourierOrderState.objects.filter(order_id__in=order_ids)
        }
