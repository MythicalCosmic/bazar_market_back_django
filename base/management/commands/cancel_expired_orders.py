from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import F
from django.utils import timezone

from base.models import Order, CouponUsage, Coupon, Product
from base.repositories.setting import SettingRepository


class Command(BaseCommand):
    help = "Cancel unpaid online-payment orders that exceeded the timeout"

    def handle(self, *args, **options):
        setting_repo = SettingRepository()
        timeout_minutes = int(setting_repo.get_value("unpaid_order_timeout_minutes", "30"))

        cutoff = timezone.now() - timedelta(minutes=timeout_minutes)

        # Only cancel orders that:
        # - Are still "pending"
        # - Use online payment (click/payme) — NOT cash
        # - Are still unpaid
        # - Were created before the cutoff
        expired = Order.objects.filter(
            status=Order.Status.PENDING,
            payment_method__in=["click", "payme"],
            payment_status=Order.PaymentStatus.UNPAID,
            created_at__lt=cutoff,
        )

        count = 0
        for order in expired:
            order.status = Order.Status.CANCELLED
            order.cancelled_at = timezone.now()
            order.cancel_reason = f"Auto-cancelled: unpaid after {timeout_minutes} minutes"
            order.save(update_fields=["status", "cancelled_at", "cancel_reason", "updated_at"])

            # Restore stock
            for item in order.items.all():
                if item.product_id:
                    Product.objects.filter(
                        pk=item.product_id, stock_qty__isnull=False
                    ).update(stock_qty=F("stock_qty") + item.quantity)

            # Restore coupon usage
            usage = CouponUsage.objects.filter(order_id=order.id).first()
            if usage:
                Coupon.objects.filter(pk=usage.coupon_id, used_count__gt=0).update(
                    used_count=F("used_count") - 1
                )
                usage.delete()

            count += 1
            self.stdout.write(f"  Cancelled {order.order_number} ({order.payment_method}, "
                              f"created {order.created_at.strftime('%H:%M')})")

        if count:
            self.stdout.write(self.style.SUCCESS(f"Cancelled {count} expired orders"))
        else:
            self.stdout.write("No expired orders found")
