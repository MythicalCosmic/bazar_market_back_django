import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from base.models import (
    User,
    Address,
    Category,
    Product,
    ProductImage,
    Banner,
    Coupon,
    DeliveryZone,
    Discount,
    Setting,
    Permission,
    RolePermission,
)


class Command(BaseCommand):
    help = "Seed the database with test data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing data before seeding",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            for model in [
                RolePermission, Permission,
                Product, ProductImage, Category, Address, User,
                Banner, Coupon, DeliveryZone, Discount, Setting,
            ]:
                model.objects.all().delete()

        self.seed_permissions()
        self.seed_users()
        self.seed_categories()
        self.seed_products()
        self.seed_addresses()
        self.seed_banners()
        self.seed_coupons()
        self.seed_discounts()
        self.seed_delivery_zones()
        self.seed_settings()

        self.stdout.write(self.style.SUCCESS("Seeding complete!"))

    def seed_permissions(self):
        from base.permissions import DEFAULT_ROLE_PERMISSIONS

        all_perms = {
            "manage_users": ("Manage users", "users"),
            "manage_roles": ("Manage roles", "users"),
            "manage_reviews": ("Manage Reviews", "reviews"),
            "manage_categories": ("Manage categories", "catalog"),
            "manage_products": ("Manage products", "catalog"),
            "manage_banners": ("Manage banners", "catalog"),
            "manage_coupons": ("Manage coupons", "catalog"),
            "manage_discounts": ("Manage discounts", "catalog"),
            "manage_delivery_zones": ("Manage delivery zones", "delivery"),
            "manage_settings": ("Manage settings", "system"),
            "manage_orders": ("Manage orders", "orders"),
            "manage_payments": ("Manage payments", "orders"),
            "manage_notifications": ("Manage notifications", "system"),
            "manage_analytics": ("Manage analytics", "system"),
            "view_users": ("View users", "users"),
            "view_categories": ("View categories", "catalog"),
            "view_reviews": ("View reviews", "reviews"),

            "view_products": ("View products", "catalog"),
            "view_orders": ("View orders", "orders"),
            "view_payments": ("View payments", "orders"),
            "view_analytics": ("View analytics", "system"),
            "view_delivery_zones": ("View delivery zones", "delivery"),
            "assign_orders": ("Assign orders", "orders"),
            "update_order_status": ("Update order status", "orders"),
            "view_assigned_orders": ("View assigned orders", "orders"),
        }

        perm_created = 0
        perm_objects = {}
        for codename, (name, group) in all_perms.items():
            obj, is_new = Permission.objects.get_or_create(
                codename=codename,
                defaults={"name": name, "group": group},
            )
            perm_objects[codename] = obj
            if is_new:
                perm_created += 1

        rp_created = 0
        for role, codenames in DEFAULT_ROLE_PERMISSIONS.items():
            for codename in codenames:
                _, is_new = RolePermission.objects.get_or_create(
                    role=role, permission=perm_objects[codename],
                )
                if is_new:
                    rp_created += 1

        self.stdout.write(f"  Permissions: {perm_created} created, {rp_created} role assignments")

    def seed_users(self):
        users = [
            {"username": "admin", "first_name": "Admin", "last_name": "Bazarov", "role": "admin", "phone": "+998901234567"},
            {"username": "manager1", "first_name": "Sardor", "last_name": "Karimov", "role": "manager", "phone": "+998901234568"},
            {"username": "manager2", "first_name": "Nilufar", "last_name": "Aliyeva", "role": "manager", "phone": "+998901234569"},
            {"username": "courier1", "first_name": "Bobur", "last_name": "Toshmatov", "role": "courier", "phone": "+998901234570", "telegram_id": 100001},
            {"username": "courier2", "first_name": "Jasur", "last_name": "Nematov", "role": "courier", "phone": "+998901234571", "telegram_id": 100002},
            {"username": "courier3", "first_name": "Otabek", "last_name": "Rakhimov", "role": "courier", "phone": "+998901234572", "telegram_id": 100003},
        ]

        clients = [
            {"first_name": "Aziza", "last_name": "Umarova", "telegram_id": 200001, "phone": "+998911111101"},
            {"first_name": "Bekzod", "last_name": "Yusupov", "telegram_id": 200002, "phone": "+998911111102"},
            {"first_name": "Charos", "last_name": "Mirzayeva", "telegram_id": 200003, "phone": "+998911111103"},
            {"first_name": "Dilshod", "last_name": "Khasanov", "telegram_id": 200004, "phone": "+998911111104"},
            {"first_name": "Elnora", "last_name": "Sultanova", "telegram_id": 200005, "phone": "+998911111105"},
            {"first_name": "Farrukh", "last_name": "Abdullayev", "telegram_id": 200006, "phone": "+998911111106"},
            {"first_name": "Gulnora", "last_name": "Rashidova", "telegram_id": 200007, "phone": "+998911111107"},
            {"first_name": "Humoyun", "last_name": "Nazarov", "telegram_id": 200008, "phone": "+998911111108"},
            {"first_name": "Iroda", "last_name": "Karimova", "telegram_id": 200009, "phone": "+998911111109"},
            {"first_name": "Javohir", "last_name": "Tursunov", "telegram_id": 200010, "phone": "+998911111110"},
        ]

        for data in clients:
            data["role"] = "client"
            data["username"] = data["first_name"].lower()
            users.append(data)

        created = 0
        for data in users:
            user, is_new = User.objects.get_or_create(
                username=data.pop("username"),
                defaults=data,
            )
            if is_new:
                user.set_password("test1234")
                created += 1

        self.stdout.write(f"  Users: {created} created, {len(users) - created} skipped")

    def seed_categories(self):
        categories = {
            "Mevalar": ["Olma", "Banan", "Uzum", "Nok", "Shaftoli", "Anor"],
            "Sabzavotlar": ["Pomidor", "Bodring", "Kartoshka", "Piyoz", "Sabzi", "Karam"],
            "Sut mahsulotlari": ["Sut", "Qatiq", "Tvorog", "Sariyog'", "Pishloq"],
            "Go'sht": ["Mol go'shti", "Tovuq", "Qo'y go'shti"],
            "Non mahsulotlari": ["Oq non", "Patir", "Lavash", "Somsa"],
            "Ichimliklar": ["Suv", "Sharbat", "Choy", "Kompot"],
        }

        created = 0
        for i, (parent_name, children) in enumerate(categories.items()):
            parent, is_new = Category.objects.get_or_create(
                name_uz=parent_name,
                defaults={"sort_order": i, "is_active": True},
            )
            if is_new:
                created += 1
            for j, child_name in enumerate(children):
                _, is_new = Category.objects.get_or_create(
                    name_uz=child_name,
                    defaults={"parent": parent, "sort_order": j, "is_active": True},
                )
                if is_new:
                    created += 1

        self.stdout.write(f"  Categories: {created} created")

    def seed_products(self):
        leaf_categories = Category.objects.filter(children__isnull=True, deleted_at__isnull=True)
        if not leaf_categories.exists():
            self.stdout.write("  Products: skipped (no categories)")
            return

        units = ["kg", "piece", "liter", "pack"]
        created = 0

        for cat in leaf_categories:
            price = Decimal(random.randint(3000, 80000))
            unit = random.choice(units)
            step = Decimal("0.5") if unit == "kg" else Decimal("1")
            min_qty = step

            product, is_new = Product.objects.get_or_create(
                name_uz=cat.name_uz,
                defaults={
                    "category": cat,
                    "name_ru": "",
                    "unit": unit,
                    "price": price,
                    "step": step,
                    "min_qty": min_qty,
                    "in_stock": True,
                    "stock_qty": Decimal(random.randint(10, 500)),
                    "is_active": True,
                    "sort_order": 0,
                },
            )
            if is_new:
                created += 1
                ProductImage.objects.create(
                    product=product,
                    image=f"https://placehold.co/400x400?text={cat.name_uz}",
                    is_primary=True,
                    sort_order=0,
                )

        self.stdout.write(f"  Products: {created} created")

    def seed_addresses(self):
        clients = User.objects.filter(role="client", deleted_at__isnull=True)
        places = [
            ("Uy", "Chilanzar 9, dom 45", "41.2856", "69.2042"),
            ("Ish", "Amir Temur ko'chasi 108", "41.3111", "69.2797"),
            ("Ota-ona", "Sergeli tumani, 7-mavze", "41.2283", "69.2289"),
        ]

        created = 0
        for user in clients:
            label, text, lat, lng = random.choice(places)
            _, is_new = Address.objects.get_or_create(
                user=user,
                label=label,
                defaults={
                    "latitude": Decimal(lat),
                    "longitude": Decimal(lng),
                    "address_text": text,
                    "is_default": True,
                    "is_active": True,
                },
            )
            if is_new:
                created += 1

        self.stdout.write(f"  Addresses: {created} created")

    def seed_banners(self):
        banners = [
            {"title": "Yangi mahsulotlar!", "image": "https://placehold.co/800x400?text=New+Products", "link_type": "none"},
            {"title": "Chegirma 20%", "image": "https://placehold.co/800x400?text=20+Off", "link_type": "none"},
            {"title": "Bepul yetkazib berish", "image": "https://placehold.co/800x400?text=Free+Delivery", "link_type": "none"},
        ]

        created = 0
        for i, data in enumerate(banners):
            _, is_new = Banner.objects.get_or_create(
                title=data["title"],
                defaults={**data, "sort_order": i, "is_active": True},
            )
            if is_new:
                created += 1

        self.stdout.write(f"  Banners: {created} created")

    def seed_coupons(self):
        coupons = [
            {"code": "YANGI2026", "type": "percent", "value": Decimal("10"), "max_discount": Decimal("20000"), "per_user_limit": 1},
            {"code": "BAZAR50", "type": "fixed", "value": Decimal("50000"), "min_order": Decimal("200000"), "per_user_limit": 2},
            {"code": "WELCOME", "type": "percent", "value": Decimal("15"), "max_discount": Decimal("30000"), "per_user_limit": 1},
        ]

        created = 0
        for data in coupons:
            _, is_new = Coupon.objects.get_or_create(
                code=data.pop("code"),
                defaults={
                    **data,
                    "is_active": True,
                    "starts_at": timezone.now(),
                    "expires_at": timezone.now() + timezone.timedelta(days=90),
                },
            )
            if is_new:
                created += 1

        self.stdout.write(f"  Coupons: {created} created")

    def seed_discounts(self):
        categories = Category.objects.filter(parent__isnull=True, deleted_at__isnull=True)[:2]
        if not categories.exists():
            self.stdout.write("  Discounts: skipped (no categories)")
            return

        created = 0
        for cat in categories:
            discount, is_new = Discount.objects.get_or_create(
                name_uz=f"{cat.name_uz} chegirma",
                defaults={
                    "type": "percent",
                    "value": Decimal("15"),
                    "max_discount": Decimal("25000"),
                    "is_active": True,
                    "starts_at": timezone.now(),
                    "expires_at": timezone.now() + timezone.timedelta(days=30),
                },
            )
            if is_new:
                discount.categories.add(cat)
                created += 1

        self.stdout.write(f"  Discounts: {created} created")

    def seed_delivery_zones(self):
        zones = [
            {"name": "Chilanzar", "delivery_fee": Decimal("10000"), "min_order": Decimal("50000"), "estimated_minutes": 30},
            {"name": "Yunusobod", "delivery_fee": Decimal("12000"), "min_order": Decimal("50000"), "estimated_minutes": 40},
            {"name": "Sergeli", "delivery_fee": Decimal("15000"), "min_order": Decimal("70000"), "estimated_minutes": 50},
            {"name": "Mirzo Ulugbek", "delivery_fee": Decimal("10000"), "min_order": Decimal("50000"), "estimated_minutes": 35},
            {"name": "Olmazor", "delivery_fee": Decimal("12000"), "min_order": Decimal("60000"), "estimated_minutes": 45},
        ]

        created = 0
        for i, data in enumerate(zones):
            _, is_new = DeliveryZone.objects.get_or_create(
                name=data.pop("name"),
                defaults={
                    **data,
                    "polygon": {"type": "Polygon", "coordinates": []},
                    "is_active": True,
                    "sort_order": i,
                },
            )
            if is_new:
                created += 1

        self.stdout.write(f"  Delivery zones: {created} created")

    def seed_settings(self):
        settings = [
            {"key": "working_hours_start", "value": "08:00", "type": "string", "description": "Store opening time"},
            {"key": "working_hours_end", "value": "22:00", "type": "string", "description": "Store closing time"},
            {"key": "min_order_total", "value": "30000", "type": "int", "description": "Minimum order total in som"},
            {"key": "max_delivery_distance_km", "value": "15", "type": "int", "description": "Max delivery radius"},
            {"key": "orders_enabled", "value": "true", "type": "bool", "description": "Accept new orders"},
            {"key": "delivery_fee", "value": "9000", "type": "int", "description": "Flat delivery fee in som"},
        ]

        created = 0
        for data in settings:
            _, is_new = Setting.objects.get_or_create(
                key=data["key"],
                defaults={
                    "value": data["value"],
                    "type": data["type"],
                    "description": data["description"],
                },
            )
            if is_new:
                created += 1

        self.stdout.write(f"  Settings: {created} created")
