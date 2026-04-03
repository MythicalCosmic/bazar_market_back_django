import uuid
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from datetime import timezone,  timedelta
import hashlib



class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None



class User(TimestampMixin, SoftDeleteMixin):
    class Role(models.TextChoices):
        CLIENT = "client", "Client"
        COURIER = "courier", "Courier"
        MANAGER = "manager", "Manager"
        ADMIN = "admin", "Admin"

    class Language(models.TextChoices):
        UZ = "uz", "O'zbekcha"
        RU = "ru", "Русский"

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    telegram_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Nullable — admin users may not have telegram",
    )
    username = models.CharField(max_length=100, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, default="")
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    language = models.CharField(max_length=5, choices=Language.choices, default=Language.UZ)
    password = models.CharField(max_length=128, blank=True, default="")
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"], name="idx_users_role"),
            models.Index(fields=["is_active"], name="idx_users_active"),
            models.Index(fields=["telegram_id"], name="idx_users_telegram"),
            models.Index(fields=["phone"], name="idx_users_phone"),
            models.Index(fields=["role", "is_active"], name="idx_users_role_active"),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} ({self.role})"

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
        self.save(update_fields=["password", "updated_at"])

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)


class Session(models.Model):
    key = models.CharField(max_length=64, primary_key=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device = models.CharField(max_length=200, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sessions"
        ordering = ["-last_activity_at"]

    def __str__(self):
        return f"{self.user} - {self.key[:12]}..."

    @classmethod
    def generate_key(cls):
        raw = f"{uuid.uuid4()}{timezone.now().isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def create_session(cls, user, ip_address="", user_agent="", device="", lifetime_hours=72):
        cls.objects.filter(user=user, is_active=False).delete()
        cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return cls.objects.create(
            key=cls.generate_key(),
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            device=device,
            expires_at=timezone.now() + timedelta(hours=lifetime_hours),
        )

    @classmethod
    def get_valid_session(cls, key):
        try:
            session = cls.objects.select_related("user").get(
                key=key, is_active=True, expires_at__gt=timezone.now()
            )
            session.save(update_fields=["last_activity_at"])
            return session
        except cls.DoesNotExist:
            return None

    def invalidate(self):
        self.is_active = False
        self.save(update_fields=["is_active"])

    @classmethod
    def invalidate_all(cls, user):
        cls.objects.filter(user=user, is_active=True).update(is_active=False)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    

class Address(TimestampMixin):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
        db_index=True,
    )
    label = models.CharField(max_length=100, blank=True, default="", help_text="Home, Work, etc.")
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    address_text = models.TextField(help_text='e.g. "Chilanzar 9, dom 45"')
    entrance = models.CharField(max_length=20, blank=True, default="")
    floor = models.CharField(max_length=10, blank=True, default="")
    apartment = models.CharField(max_length=20, blank=True, default="")
    comment = models.TextField(blank=True, default="", help_text="Delivery instructions")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "addresses"
        indexes = [
            models.Index(fields=["user_id"], name="idx_addresses_user"),
            models.Index(fields=["user_id", "is_default"], name="idx_addresses_user_default"),
            models.Index(fields=["user_id", "is_active"], name="idx_addresses_user_active"),
        ]

    def __str__(self) -> str:
        return f"{self.label or 'Address'} — {self.address_text[:40]}"



class Category(TimestampMixin, SoftDeleteMixin):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="Self-ref for subcategories: Fruits > Apples",
    )
    name_uz = models.CharField(max_length=200)
    name_ru = models.CharField(max_length=200, blank=True, default="")
    image = models.CharField(max_length=500, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        ordering = ["sort_order"]
        indexes = [
            models.Index(fields=["parent_id"], name="idx_categories_parent"),
            models.Index(fields=["sort_order"], name="idx_categories_sort"),
            models.Index(fields=["is_active"], name="idx_categories_active"),
            models.Index(fields=["is_active", "sort_order"], name="idx_categories_active_sort"),
        ]

    def __str__(self) -> str:
        return self.name_uz


class Product(TimestampMixin, SoftDeleteMixin):
    class Unit(models.TextChoices):
        KG = "kg", "Kilogram"
        PIECE = "piece", "Piece"
        LITER = "liter", "Liter"
        PACK = "pack", "Pack"
        BUNDLE = "bundle", "Bundle"

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name_uz = models.CharField(max_length=300)
    name_ru = models.CharField(max_length=300, blank=True, default="")
    description_uz = models.TextField(blank=True, default="")
    description_ru = models.TextField(blank=True, default="")

    # Pricing & units
    unit = models.CharField(max_length=20, choices=Unit.choices)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price per 1 unit",
    )
    step = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        default=1,
        help_text="0.5 = buy in 0.5kg steps",
    )
    min_qty = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        default=1,
        help_text="Minimum order: 0.5kg, 1 piece",
    )
    max_qty = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="null = unlimited",
    )

    # Stock
    in_stock = models.BooleanField(default=True)
    stock_qty = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="null = unlimited stock",
    )

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        db_table = "products"
        ordering = ["sort_order"]
        indexes = [
            models.Index(fields=["category_id"], name="idx_products_category"),
            models.Index(fields=["is_active"], name="idx_products_active"),
            models.Index(fields=["is_active", "in_stock"], name="idx_products_available"),
            models.Index(fields=["category_id", "sort_order"], name="idx_products_cat_sort"),
            models.Index(fields=["uuid"], name="idx_products_uuid"),
            models.Index(fields=["price"], name="idx_products_price"),
            models.Index(fields=["is_featured", "sort_order"], name="idx_products_featured_sort"),
        ]

    def __str__(self) -> str:
        return self.name_uz


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.CharField(max_length=500)
    sort_order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "product_images"
        ordering = ["sort_order"]
        indexes = [
            models.Index(fields=["product_id", "sort_order"], name="idx_prod_img_sort"),
            models.Index(fields=["product_id", "is_primary"], name="idx_prod_img_primary"),
        ]

    def __str__(self) -> str:
        return f"Image for {self.product_id} (#{self.sort_order})"


class Banner(TimestampMixin):
    class LinkType(models.TextChoices):
        CATEGORY = "category", "Category"
        PRODUCT = "product", "Product"
        URL = "url", "URL"
        NONE = "none", "None"

    title = models.CharField(max_length=200, blank=True, default="")
    image = models.CharField(max_length=500)
    link_type = models.CharField(max_length=30, choices=LinkType.choices, default=LinkType.NONE)
    link_value = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="category_id, product_id, or URL",
    )
    sort_order = models.IntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "banners"
        ordering = ["sort_order"]
        indexes = [
            models.Index(
                fields=["is_active", "starts_at", "expires_at"],
                name="idx_banners_active",
            ),
        ]

    def __str__(self) -> str:
        return self.title or f"Banner #{self.pk}"


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="+")
    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(0)],
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cart_items"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="uq_cart_user_product",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id"], name="idx_cart_user"),
        ]

    def __str__(self) -> str:
        return f"Cart: {self.user_id} × {self.product_id} ({self.quantity})"


class Order(TimestampMixin):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PREPARING = "preparing", "Preparing"
        DELIVERING = "delivering", "Delivering"
        DELIVERED = "delivered", "Delivered"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        CLICK = "click", "Click"
        PAYME = "payme", "Payme"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text='e.g. "ORD-20260323-0042"',
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    assigned_courier = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders",
    )

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Money
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    # Payment
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        null=True,
        blank=True,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )

    # Delivery snapshot
    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    delivery_address_text = models.TextField(blank=True, default="", help_text="Frozen at order time")
    delivery_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    delivery_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    scheduled_time = models.DateTimeField(null=True, blank=True, help_text="null = ASAP")

    # Notes
    user_note = models.TextField(blank=True, default="")
    admin_note = models.TextField(blank=True, default="")
    cancel_reason = models.TextField(blank=True, default="")

    # Status timestamps
    confirmed_at = models.DateTimeField(null=True, blank=True)
    preparing_at = models.DateTimeField(null=True, blank=True)
    delivering_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id"], name="idx_orders_user"),
            models.Index(fields=["status"], name="idx_orders_status"),
            models.Index(fields=["created_at"], name="idx_orders_created"),
            models.Index(fields=["status", "created_at"], name="idx_orders_active"),
            models.Index(fields=["user_id", "created_at"], name="idx_orders_user_history"),
            models.Index(fields=["created_at", "status"], name="idx_orders_daily_analytics"),
            models.Index(fields=["payment_status"], name="idx_orders_pay_status"),
            models.Index(fields=["order_number"], name="idx_orders_number"),
            models.Index(fields=["assigned_courier_id", "status"], name="idx_orders_courier_status"),
        ]

    def __str__(self) -> str:
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
    )

    # Snapshot at order time
    product_name = models.CharField(max_length=300)
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.DecimalField(max_digits=8, decimal_places=3)
    total = models.DecimalField(max_digits=12, decimal_places=2, help_text="unit_price × quantity")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_items"
        indexes = [
            models.Index(fields=["order_id"], name="idx_order_items_order"),
            models.Index(fields=["product_id"], name="idx_order_items_product"),
        ]

    def __str__(self) -> str:
        return f"{self.product_name} ×{self.quantity}"


class OrderStatusLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_logs")
    from_status = models.CharField(max_length=20, blank=True, default="")
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Which admin/system changed it",
    )
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_status_log"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["order_id"], name="idx_status_log_order"),
            models.Index(fields=["created_at"], name="idx_status_log_created"),
        ]

    def __str__(self) -> str:
        return f"{self.order_id}: {self.from_status} → {self.to_status}"



class Payment(TimestampMixin):
    class Method(models.TextChoices):
        CLICK = "click", "Click"
        PAYME = "payme", "Payme"
        CASH = "cash", "Cash"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    method = models.CharField(max_length=20, choices=Method.choices)
    external_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Transaction ID from Click/Payme",
        db_index=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Raw provider response for debugging",
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments"
        indexes = [
            models.Index(fields=["order_id"], name="idx_payments_order"),
            models.Index(fields=["external_id"], name="idx_payments_external"),
            models.Index(fields=["status"], name="idx_payments_status"),
            models.Index(fields=["method", "status"], name="idx_payments_method_status"),
        ]

    def __str__(self) -> str:
        return f"Payment {self.uuid} ({self.method} — {self.status})"


class Coupon(TimestampMixin):
    class Type(models.TextChoices):
        PERCENT = "percent", "Percent"
        FIXED = "fixed", "Fixed"

    code = models.CharField(max_length=30, unique=True, help_text='e.g. "YANGI2026"')
    type = models.CharField(max_length=20, choices=Type.choices)
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="10 for 10% or 10000 for 10k som",
    )
    min_order = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum order total to apply",
    )
    max_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cap for percent type",
    )
    usage_limit = models.IntegerField(null=True, blank=True, help_text="Total uses, null = unlimited")
    per_user_limit = models.IntegerField(default=1)
    used_count = models.IntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "coupons"
        indexes = [
            models.Index(fields=["code"], name="idx_coupons_code"),
            models.Index(
                fields=["is_active", "starts_at", "expires_at"],
                name="idx_coupons_active",
            ),
        ]

    def __str__(self) -> str:
        return self.code


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="coupon_usages")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="coupon_usages")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "coupon_usages"
        indexes = [
            models.Index(fields=["coupon_id", "user_id"], name="idx_coupon_usage_user"),
        ]

    def __str__(self) -> str:
        return f"{self.coupon.code} used by {self.user_id}"



class Discount(TimestampMixin, SoftDeleteMixin):
    class Type(models.TextChoices):
        PERCENT = "percent", "Percent"
        FIXED = "fixed", "Fixed"

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    name_uz = models.CharField(max_length=200)
    name_ru = models.CharField(max_length=200, blank=True, default="")
    type = models.CharField(max_length=20, choices=Type.choices)
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="10 for 10% or 10000 for 10k som",
    )
    max_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cap for percent type",
    )
    products = models.ManyToManyField(
        "Product",
        blank=True,
        related_name="discounts",
    )
    categories = models.ManyToManyField(
        "Category",
        blank=True,
        related_name="discounts",
    )
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "discounts"
        indexes = [
            models.Index(
                fields=["is_active", "starts_at", "expires_at"],
                name="idx_discounts_active",
            ),
        ]

    def __str__(self) -> str:
        return self.name_uz


class DeliveryZone(TimestampMixin):
    name = models.CharField(max_length=100, help_text='e.g. "Chilanzar", "Sergeli"')
    polygon = models.JSONField(help_text="GeoJSON polygon coordinates")
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    min_order = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Minimum order for this zone",
    )
    estimated_minutes = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="30, 45, 60",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "delivery_zones"
        ordering = ["sort_order"]
        indexes = [
            models.Index(fields=["is_active"], name="idx_zones_active"),
        ]

    def __str__(self) -> str:
        return self.name


class Notification(models.Model):
    class Type(models.TextChoices):
        ORDER_STATUS = "order_status", "Order Status"
        PROMO = "promo", "Promo"
        SYSTEM = "system", "System"

    class Channel(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        SMS = "sms", "SMS"
        PUSH = "push", "Push"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=300, blank=True, default="")
    body = models.TextField(blank=True, default="")
    payload = models.JSONField(null=True, blank=True, help_text='{"order_id": 123} for deep linking')
    channel = models.CharField(max_length=20, choices=Channel.choices)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["user_id", "is_read"], name="idx_notif_user_read"),
            models.Index(fields=["sent_at"], name="idx_notif_sent"),
            models.Index(fields=["user_id", "sent_at"], name="idx_notif_user_sent"),
        ]

    def __str__(self) -> str:
        return f"{self.type}: {self.title[:50]}"



class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "favorites"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="uq_favorite_user_product",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} ♥ {self.product_id}"


class Review(models.Model):
    class ModerationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True, default="")
    admin_reply = models.TextField(blank=True, default="")
    moderation_status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PENDING,
    )
    moderated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reviews"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "order"],
                name="uq_review_user_order",
            ),
        ]
        indexes = [
            models.Index(fields=["order_id"], name="idx_reviews_order"),
            models.Index(fields=["rating"], name="idx_reviews_rating"),
            models.Index(fields=["moderation_status"], name="idx_reviews_moderation"),
        ]

    def __str__(self) -> str:
        return f"Review {self.order_id} — {self.rating}★"


class Referral(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referrals_given")
    referred = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referral_received")
    reward_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    is_rewarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "referrals"
        constraints = [
            models.UniqueConstraint(fields=["referred"], name="uq_referral_referred"),
        ]
        indexes = [
            models.Index(fields=["referrer_id"], name="idx_referrals_referrer"),
        ]

    def __str__(self) -> str:
        return f"{self.referrer_id} → {self.referred_id}"



class DailyStat(models.Model):
    date = models.DateField(unique=True)
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_users = models.IntegerField(default=0, help_text="Unique users who ordered")
    avg_order_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    top_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "daily_stats"
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["date"], name="idx_daily_stats_date"),
        ]

    def __str__(self) -> str:
        return f"Stats {self.date}: {self.total_orders} orders"


class SearchLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    query = models.CharField(max_length=300)
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_logs"
        indexes = [
            models.Index(fields=["created_at"], name="idx_search_logs_created"),
            models.Index(fields=["query"], name="idx_search_logs_query"),
        ]

    def __str__(self) -> str:
        return f'"{self.query}" ({self.results_count} results)'



class Permission(models.Model):
    codename = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    group = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "permissions"
        ordering = ["group", "codename"]

    def __str__(self) -> str:
        return self.codename


class RolePermission(models.Model):
    role = models.CharField(max_length=20, choices=User.Role.choices, db_index=True)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")

    class Meta:
        db_table = "role_permissions"
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="uq_role_permission"),
        ]
        indexes = [
            models.Index(fields=["role"], name="idx_role_perm_role"),
        ]

    def __str__(self) -> str:
        return f"{self.role} -> {self.permission.codename}"


class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="user_permissions")
    is_granted = models.BooleanField(default=True)

    class Meta:
        db_table = "user_permissions"
        constraints = [
            models.UniqueConstraint(fields=["user", "permission"], name="uq_user_permission"),
        ]
        indexes = [
            models.Index(fields=["user_id"], name="idx_user_perm_user"),
        ]

    def __str__(self) -> str:
        prefix = "+" if self.is_granted else "-"
        return f"{prefix}{self.permission.codename} for {self.user}"


class Setting(models.Model):
    class ValueType(models.TextChoices):
        STRING = "string", "String"
        INT = "int", "Integer"
        BOOL = "bool", "Boolean"
        JSON = "json", "JSON"

    key = models.CharField(
        max_length=100,
        primary_key=True,
        help_text='e.g. "working_hours_start", "min_order_total"',
    )
    value = models.TextField()
    type = models.CharField(max_length=20, choices=ValueType.choices, default=ValueType.STRING)
    description = models.CharField(max_length=300, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settings"

    def __str__(self) -> str:
        return f"{self.key} = {self.value[:50]}"