from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from base.interfaces.cart import ICartItemRepository
from base.interfaces.product import IProductRepository
from base.interfaces.order import IOrderRepository, IOrderItemRepository, IOrderStatusLogRepository
from base.interfaces.coupon import ICouponRepository, ICouponUsageRepository
from base.interfaces.address import IAddressRepository
from base.interfaces.setting import ISettingRepository
from base.interfaces.discount import IDiscountRepository
from base.exceptions import NotFoundError, ValidationError
from base.models import Order, Discount
from customer.dto.order import PlaceOrderDTO
from customer.services.v1.coupon_service import CustomerCouponService


VALID_PAYMENT_METHODS = {"cash", "card"}


class CustomerOrderService:
    def __init__(
        self,
        cart_repository: ICartItemRepository,
        product_repository: IProductRepository,
        order_repository: IOrderRepository,
        order_item_repository: IOrderItemRepository,
        order_status_log_repository: IOrderStatusLogRepository,
        coupon_repository: ICouponRepository,
        coupon_usage_repository: ICouponUsageRepository,
        address_repository: IAddressRepository,
        delivery_zone_repository: IDeliveryZoneRepository,
        setting_repository: ISettingRepository,
        discount_repository: IDiscountRepository,
    ):
        self.cart_repo = cart_repository
        self.product_repo = product_repository
        self.order_repo = order_repository
        self.item_repo = order_item_repository
        self.log_repo = order_status_log_repository
        self.coupon_repo = coupon_repository
        self.usage_repo = coupon_usage_repository
        self.address_repo = address_repository
        self.zone_repo = delivery_zone_repository
        self.setting_repo = setting_repository
        self.discount_repo = discount_repository

    @transaction.atomic
    def place_order(self, user_id: int, dto: PlaceOrderDTO) -> dict:
        # 1. Cart
        cart_items = list(self.cart_repo.get_by_user(user_id))
        if not cart_items:
            raise ValidationError("Cart is empty")

        # 2. Address
        address = (
            self.address_repo.get_all()
            .filter(pk=dto.address_id, user_id=user_id, is_active=True)
            .first()
        )
        if not address:
            raise ValidationError("Address not found")

        # 3. Payment method
        if dto.payment_method not in VALID_PAYMENT_METHODS:
            raise ValidationError(f"Invalid payment method. Must be one of: {', '.join(VALID_PAYMENT_METHODS)}")

        # 4. Validate products
        errors = []
        for ci in cart_items:
            p = ci.product
            if not p or p.deleted_at or not p.is_active:
                errors.append(f"'{ci.product_id}' is no longer available")
                continue
            if not p.in_stock:
                errors.append(f"'{p.name_uz}' is out of stock")
                continue
            if p.stock_qty is not None and ci.quantity > p.stock_qty:
                errors.append(f"'{p.name_uz}' only has {p.stock_qty} in stock")
        if errors:
            raise ValidationError("Some products are unavailable", errors=errors)

        # 5. Apply product discounts and calculate subtotal
        discounted_prices = self._get_discounted_prices(cart_items)
        subtotal = sum(discounted_prices[ci.product_id] * ci.quantity for ci in cart_items)

        # Track how much was saved from product discounts
        product_discount = sum(
            (ci.product.price - discounted_prices[ci.product_id]) * ci.quantity
            for ci in cart_items
        )

        # 6. Delivery fee (from settings) & global minimum order
        delivery_fee = Decimal(str(self.setting_repo.get_value("delivery_fee", "0")))
        global_min = Decimal(str(self.setting_repo.get_value("min_order_total", "0")))
        if global_min > 0 and subtotal < global_min:
            raise ValidationError(f"Minimum order total is {global_min}")

        # 8. Coupon (applied on top of product discounts)
        coupon_discount = Decimal(0)
        coupon = None
        if dto.coupon_code:
            coupon_svc = CustomerCouponService(self.coupon_repo, self.usage_repo)
            coupon_svc.validate_coupon(user_id, dto.coupon_code, subtotal)

            coupon = self.coupon_repo.get_by_code(dto.coupon_code.upper())
            coupon_discount = coupon_svc.calculate_discount(coupon, subtotal)

        # 9. Total
        total_discount = product_discount + coupon_discount
        total = subtotal + delivery_fee - coupon_discount
        if total < 0:
            total = Decimal(0)

        # 10. Scheduled time
        scheduled_time = None
        if dto.scheduled_time:
            scheduled_time = parse_datetime(dto.scheduled_time)
            if not scheduled_time:
                raise ValidationError("Invalid scheduled_time format")
            if scheduled_time.tzinfo is None:
                scheduled_time = timezone.make_aware(scheduled_time)
            if scheduled_time < timezone.now():
                raise ValidationError("scheduled_time cannot be in the past")

        # 11. Generate order number
        order_number = self._generate_order_number()

        # 12. Create order
        order = self.order_repo.create(
            order_number=order_number,
            user_id=user_id,
            status=Order.Status.PENDING,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            discount=total_discount,
            total=total,
            payment_method=dto.payment_method,
            payment_status=Order.PaymentStatus.UNPAID,
            address=address,
            delivery_address_text=address.address_text,
            delivery_lat=address.latitude,
            delivery_lng=address.longitude,
            user_note=dto.user_note,
            scheduled_time=scheduled_time,
        )

        # 13. Create order items (snapshot with discounted prices)
        items_data = [
            {
                "product_id": ci.product_id,
                "product_name": ci.product.name_uz,
                "unit": ci.product.unit,
                "unit_price": discounted_prices[ci.product_id],
                "quantity": ci.quantity,
                "total": discounted_prices[ci.product_id] * ci.quantity,
            }
            for ci in cart_items
        ]
        self.item_repo.bulk_create_items(order, items_data)

        # 14. Deduct stock
        for ci in cart_items:
            if ci.product.stock_qty is not None:
                updated = self.product_repo.decrease_stock(ci.product_id, ci.quantity)
                if updated == 0:
                    raise ValidationError(f"'{ci.product.name_uz}' went out of stock")

        # 15. Record coupon usage
        if coupon:
            self.coupon_repo.increment_usage(coupon)
            self.usage_repo.record_usage(coupon.id, user_id, order.id, coupon_discount)

        # 16. Log status
        self.log_repo.log_transition(
            order_id=order.id,
            from_status="",
            to_status="pending",
            changed_by_id=user_id,
            note="Order placed",
        )

        # 17. Clear cart
        self.cart_repo.clear_cart(user_id)

        # 18. Notify admins via Telegram
        try:
            from bot.notify import notify_admins_new_order
            notify_admins_new_order(order)
        except Exception:
            pass  # Non-critical

        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "subtotal": str(subtotal),
            "delivery_fee": str(delivery_fee),
            "discount": str(total_discount),
            "total": str(total),
            "payment_method": dto.payment_method,
        }

    def _get_discounted_prices(self, cart_items) -> dict:
        """Batch-fetch active discounts and compute best price per product."""
        now = timezone.now()
        product_ids = [ci.product_id for ci in cart_items]
        category_ids = list({ci.product.category_id for ci in cart_items})

        discounts = list(
            Discount.objects.filter(
                is_active=True, deleted_at__isnull=True,
            ).filter(
                Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                Q(expires_at__isnull=True) | Q(expires_at__gte=now),
            ).filter(
                Q(products__in=product_ids) | Q(categories__in=category_ids)
            ).distinct().prefetch_related("products", "categories")
        )

        prices = {}
        for ci in cart_items:
            p = ci.product
            best_price = p.price

            for d in discounts:
                d_product_ids = set(d.products.values_list("id", flat=True))
                d_category_ids = set(d.categories.values_list("id", flat=True))

                if p.id not in d_product_ids and p.category_id not in d_category_ids:
                    continue

                if d.type == "percent":
                    disc = p.price * d.value / Decimal(100)
                    if d.max_discount:
                        disc = min(disc, d.max_discount)
                else:
                    disc = min(d.value, p.price)

                candidate = p.price - disc
                if candidate < best_price:
                    best_price = candidate

            prices[p.id] = max(best_price, Decimal(0))
        return prices

    def list_orders(self, user_id: int, status=None, page=1, per_page=20):
        qs = self.order_repo.get_by_user(user_id).select_related("address")
        if status:
            qs = qs.filter(status=status)
        qs = qs.order_by("-created_at")
        return self.order_repo.paginate(qs, page, per_page)

    def get_order(self, user_id: int, order_id: int):
        order = (
            self.order_repo.get_all()
            .select_related("address")
            .filter(pk=order_id, user_id=user_id)
            .first()
        )
        if not order:
            return None

        order._items = list(self.item_repo.get_by_order(order_id))
        order._status_log = list(self.log_repo.get_by_order(order_id))
        return order

    def active_orders(self, user_id: int) -> list:
        return list(
            self.order_repo.get_active_by_user(user_id)
            .select_related("address")
            .order_by("-created_at")
        )

    @transaction.atomic
    def cancel_order(self, user_id: int, order_id: int, reason: str = "") -> dict:
        order = (
            Order.objects.select_for_update()
            .filter(pk=order_id, user_id=user_id)
            .first()
        )
        if not order:
            raise NotFoundError("Order not found")

        if order.status != "pending":
            raise ValidationError("Only pending orders can be cancelled")

        self.order_repo.cancel(order, reason=reason or "Cancelled by customer")

        self.log_repo.log_transition(
            order_id=order.id,
            from_status="pending",
            to_status="cancelled",
            changed_by_id=user_id,
            note=reason or "Cancelled by customer",
        )

        # Restore stock
        items = self.item_repo.get_by_order(order_id)
        for item in items:
            if item.product_id:
                self.product_repo.increase_stock(item.product_id, item.quantity)

        # Decrement coupon usage
        from base.models import CouponUsage
        usage = CouponUsage.objects.filter(order_id=order_id).first()
        if usage:
            self.coupon_repo.decrement_usage(
                self.coupon_repo.get_by_id(usage.coupon_id)
            )
            usage.delete()

        return {"order_id": order.id, "status": "cancelled"}

    def reorder(self, user_id: int, order_id: int) -> dict:
        order = self.order_repo.get_all().filter(pk=order_id, user_id=user_id).first()
        if not order:
            raise NotFoundError("Order not found")

        items = self.item_repo.get_by_order(order_id)
        added = []
        skipped = []

        for item in items:
            if not item.product_id:
                skipped.append(item.product_name)
                continue

            product = self.product_repo.get_by_id(item.product_id)
            if not product or not product.is_active or not product.in_stock:
                skipped.append(item.product_name)
                continue

            qty = item.quantity
            if product.stock_qty is not None and qty > product.stock_qty:
                qty = product.stock_qty

            if qty > 0:
                self.cart_repo.add_item(user_id, item.product_id, qty)
                added.append(item.product_name)
            else:
                skipped.append(item.product_name)

        return {
            "added": added,
            "skipped": skipped,
            "message": f"{len(added)} items added to cart",
        }

    @staticmethod
    def _generate_order_number() -> str:
        now = timezone.now()
        date_str = now.strftime("%Y%m%d")
        prefix = f"ORD-{date_str}-"

        count = Order.objects.filter(order_number__startswith=prefix).count()
        seq = count + 1

        return f"{prefix}{seq:04d}"
