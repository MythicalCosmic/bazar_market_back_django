"""Courier mobile-app models (the "Market" courier app).

Server-side state the courier app needs on top of the shared base models:

  CourierProfile    — rider profile + online flag + UI prefs (1:1 with base.User)
  CourierOrderState — the courier's status projection of an assigned order
                      (new → accepted → picked → onway → delivered), kept
                      separate from base.Order.status (admin/kitchen-driven)
  PushDevice        — Expo/FCM push token registered after login

Money everywhere on the wire is integer so'm; the DB keeps Decimal (base.Order),
serializers coerce to int.
"""
from decimal import Decimal

from django.db import models

from base.models import TimestampMixin, User, Order


class CourierProfile(TimestampMixin):
    class Vehicle(models.TextChoices):
        MOTORCYCLE = "motorcycle", "Motorcycle"
        CAR = "car", "Car"
        BICYCLE = "bicycle", "Bicycle"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="courier_profile"
    )
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("5.00"))
    vehicle_type = models.CharField(
        max_length=20, choices=Vehicle.choices, default=Vehicle.MOTORCYCLE
    )
    vehicle_plate = models.CharField(max_length=20, blank=True, default="")
    is_online = models.BooleanField(default=False)
    # App UI prefs: {push, sound, accent, dark}. `lang` lives on User.language.
    prefs = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "courier_profiles"

    def __str__(self) -> str:
        return f"CourierProfile<{self.user_id}>"


class CourierOrderState(TimestampMixin):
    class Status(models.TextChoices):
        NEW = "new", "New"
        ACCEPTED = "accepted", "Accepted"
        PICKED = "picked", "Picked up"
        ONWAY = "onway", "On the way"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    # Forward-only flow the courier advances through (cancelled is terminal and
    # set out-of-band when the order itself is cancelled, never by the courier).
    FLOW = ["new", "accepted", "picked", "onway", "delivered"]

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="courier_state"
    )
    courier = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="courier_states"
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.NEW, db_index=True
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    picked_at = models.DateTimeField(null=True, blank=True)
    onway_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "courier_order_states"
        indexes = [
            models.Index(fields=["courier", "status"], name="idx_courier_state_cs"),
        ]

    def __str__(self) -> str:
        return f"CourierOrderState<order={self.order_id} {self.status}>"

    def can_advance_to(self, target: str) -> bool:
        """True only if `target` is the immediate next step in FLOW."""
        try:
            return self.FLOW.index(target) == self.FLOW.index(self.status) + 1
        except ValueError:
            return False


class PushDevice(TimestampMixin):
    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="push_devices"
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=16, blank=True, default="")

    class Meta:
        db_table = "push_devices"
        indexes = [
            models.Index(fields=["user"], name="idx_push_devices_user"),
        ]

    def __str__(self) -> str:
        return f"PushDevice<{self.user_id}:{self.platform}>"
