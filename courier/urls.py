"""Market courier mobile-app routes. Mounted at /courier-api/ (see project urls).

So the app's base URL is e.g. https://api.bazarmarket.org/courier-api
All responses use the standard {success, data} envelope; the spec shapes are the
`data` payload.
"""
from django.urls import path

from courier.views.v1.auth_views import login_view, refresh_view, logout_view
from courier.views.v1.profile_views import me_view, online_view, prefs_view
from courier.views.v1.dashboard_views import stats_view
from courier.views.v1.order_views import (
    active_orders_view,
    order_detail_view,
    update_status_view,
    advance_status_view,
    history_view,
)
from courier.views.v1.device_views import register_device_view, unregister_device_view

app_name = "courier"

urlpatterns = [
    # ── Auth ──
    path("auth/login", login_view, name="login"),
    path("auth/refresh", refresh_view, name="refresh"),
    path("auth/logout", logout_view, name="logout"),

    # ── Profile / presence ──
    path("me", me_view, name="me"),
    path("me/online", online_view, name="me-online"),
    path("me/prefs", prefs_view, name="me-prefs"),

    # ── Dashboard ──
    path("dashboard/stats", stats_view, name="dashboard-stats"),

    # ── Orders (exact paths before the <ref> catch-all) ──
    path("orders/active", active_orders_view, name="orders-active"),
    path("orders/history", history_view, name="orders-history"),
    path("orders/<str:ref>", order_detail_view, name="order-detail"),
    path("orders/<str:ref>/status", update_status_view, name="order-status"),
    path("orders/<str:ref>/advance", advance_status_view, name="order-advance"),

    # ── Push devices ──
    path("devices", register_device_view, name="devices"),
    # <path:> (not <str:>) so tokens containing "/" (FCM) still match; the token
    # may also be sent in the request body to keep it out of access logs.
    path("devices/<path:token>", unregister_device_view, name="device-delete"),
]
