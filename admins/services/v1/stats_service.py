from django.db.models import Count, Sum, Avg, F
from django.utils import timezone
from datetime import timedelta

from base.models import User, Order, Product, Category


STAFF_ROLES = {User.Role.ADMIN, User.Role.MANAGER, User.Role.COURIER}


class StatsService:

    def staff_stats(self, date_from=None, date_to=None) -> dict:
        staff = User.objects.filter(role__in=STAFF_ROLES, deleted_at__isnull=True)
        if date_from:
            staff = staff.filter(created_at__gte=date_from)
        if date_to:
            staff = staff.filter(created_at__lte=date_to)
        return {
            "total": staff.count(),
            "by_role": dict(
                staff.values_list("role").annotate(c=Count("id")).values_list("role", "c")
            ),
            "active": staff.filter(is_active=True).count(),
            "inactive": staff.filter(is_active=False).count(),
        }

    def customer_stats(self, reference_lat=None, reference_lng=None, date_from=None, date_to=None) -> dict:
        customers = User.objects.filter(role=User.Role.CLIENT, deleted_at__isnull=True)
        if date_from:
            customers = customers.filter(created_at__gte=date_from)
        if date_to:
            customers = customers.filter(created_at__lte=date_to)

        total = customers.count()
        active = customers.filter(is_active=True).count()

        orders = Order.objects.filter(user__role=User.Role.CLIENT)
        if date_from:
            orders = orders.filter(created_at__gte=date_from)
        if date_to:
            orders = orders.filter(created_at__lte=date_to)
        completed = orders.exclude(status__in=["cancelled"])

        buyers = completed.values("user").distinct().count()
        agg = completed.aggregate(
            total_revenue=Sum("total"),
            avg_order=Avg("total"),
            total_orders=Count("id"),
        )

        top_spenders = list(
            completed.values("user_id", "user__first_name", "user__last_name", "user__phone")
            .annotate(total_spent=Sum("total"), order_count=Count("id"))
            .order_by("-total_spent")[:5]
        )

        least_buyers = list(
            completed.values("user_id", "user__first_name", "user__last_name", "user__phone")
            .annotate(order_count=Count("id"))
            .order_by("order_count")[:5]
        )

        most_frequent = list(
            completed.values("user_id", "user__first_name", "user__last_name", "user__phone")
            .annotate(order_count=Count("id"))
            .order_by("-order_count")[:5]
        )

        now = timezone.now()
        all_customers = User.objects.filter(role=User.Role.CLIENT, deleted_at__isnull=True)
        new_7d = all_customers.filter(created_at__gte=now - timedelta(days=7)).count()
        new_30d = all_customers.filter(created_at__gte=now - timedelta(days=30)).count()
        active_buyers_30d = (
            Order.objects.filter(
                user__role=User.Role.CLIENT,
                created_at__gte=now - timedelta(days=30),
            )
            .exclude(status="cancelled")
            .values("user").distinct().count()
        )

        all_total = all_customers.count()
        all_buyers = (
            Order.objects.filter(user__role=User.Role.CLIENT)
            .exclude(status="cancelled")
            .values("user").distinct().count()
        )
        never_ordered = all_total - all_buyers

        result = {
            "total_customers": total,
            "active_customers": active,
            "new_last_7d": new_7d,
            "new_last_30d": new_30d,
            "customers_who_bought": buyers,
            "never_ordered": never_ordered,
            "active_buyers_30d": active_buyers_30d,
            "total_revenue": str(agg["total_revenue"] or 0),
            "avg_order_value": str(round(agg["avg_order"] or 0, 2)),
            "total_orders": agg["total_orders"],
            "top_spenders": [
                {
                    "id": s["user_id"],
                    "name": f"{s['user__first_name']} {s['user__last_name']}",
                    "phone": s["user__phone"],
                    "total_spent": str(s["total_spent"]),
                    "order_count": s["order_count"],
                }
                for s in top_spenders
            ],
            "most_frequent_buyers": [
                {
                    "id": s["user_id"],
                    "name": f"{s['user__first_name']} {s['user__last_name']}",
                    "phone": s["user__phone"],
                    "order_count": s["order_count"],
                }
                for s in most_frequent
            ],
            "least_buyers": [
                {
                    "id": s["user_id"],
                    "name": f"{s['user__first_name']} {s['user__last_name']}",
                    "phone": s["user__phone"],
                    "order_count": s["order_count"],
                }
                for s in least_buyers
            ],
        }

        if reference_lat is not None and reference_lng is not None:
            from base.models import Address
            from django.db.models.functions import Abs

            addresses = (
                Address.objects.filter(
                    user__role=User.Role.CLIENT,
                    is_active=True,
                    is_default=True,
                )
                .annotate(
                    dist=Abs(F("latitude") - reference_lat) + Abs(F("longitude") - reference_lng)
                )
                .select_related("user")
            )

            farthest = addresses.order_by("-dist").first()
            nearest = addresses.order_by("dist").first()

            def _addr_data(addr):
                if not addr:
                    return None
                return {
                    "id": addr.user_id,
                    "name": f"{addr.user.first_name} {addr.user.last_name}",
                    "address": addr.address_text,
                    "lat": str(addr.latitude),
                    "lng": str(addr.longitude),
                }

            result["farthest_customer"] = _addr_data(farthest)
            result["nearest_customer"] = _addr_data(nearest)

        return result

    def overview(self, date_from=None, date_to=None) -> dict:
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if date_from and date_to:
            orders = Order.objects.filter(created_at__gte=date_from, created_at__lte=date_to)
            completed = orders.exclude(status="cancelled")
            return {
                "orders": orders.count(),
                "revenue": str(completed.aggregate(s=Sum("total"))["s"] or 0),
                "total_products": Product.objects.filter(is_active=True, deleted_at__isnull=True).count(),
                "total_categories": Category.objects.filter(is_active=True, deleted_at__isnull=True).count(),
                "pending_orders": Order.objects.filter(status="pending").count(),
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
            }

        orders_today = Order.objects.filter(created_at__gte=today)
        orders_7d = Order.objects.filter(created_at__gte=now - timedelta(days=7))

        return {
            "orders_today": orders_today.count(),
            "revenue_today": str(
                orders_today.exclude(status="cancelled").aggregate(s=Sum("total"))["s"] or 0
            ),
            "orders_7d": orders_7d.count(),
            "revenue_7d": str(
                orders_7d.exclude(status="cancelled").aggregate(s=Sum("total"))["s"] or 0
            ),
            "total_products": Product.objects.filter(is_active=True, deleted_at__isnull=True).count(),
            "total_categories": Category.objects.filter(is_active=True, deleted_at__isnull=True).count(),
            "pending_orders": Order.objects.filter(status="pending").count(),
        }
