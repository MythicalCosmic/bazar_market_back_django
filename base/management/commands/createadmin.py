import getpass

from django.core.management.base import BaseCommand

from base.models import User, Permission, RolePermission
from base.permissions import DEFAULT_ROLE_PERMISSIONS


class Command(BaseCommand):
    help = "Create an admin or staff user interactively"

    ROLE_CHOICES = ["admin", "manager", "courier"]

    def add_arguments(self, parser):
        parser.add_argument("--no-input", action="store_true", help="Use defaults, only ask for required fields")

    def handle(self, *args, **options):
        self.stdout.write("\n  Create Staff User\n  " + "=" * 30 + "\n")

        role = self._ask_choice("Role", self.ROLE_CHOICES, default="admin")
        username = self._ask("Username", required=True)
        first_name = self._ask("First name", required=True)
        last_name = self._ask("Last name", default="")
        phone = self._ask("Phone (e.g. +998901234567)", default="") or None
        telegram_id = self._ask("Telegram ID (number, leave blank if none)", default="")
        telegram_id = int(telegram_id) if telegram_id else None
        language = self._ask_choice("Language", ["uz", "ru"], default="uz")

        # Password
        while True:
            password = getpass.getpass("Password: ")
            if not password:
                self.stderr.write("  Password cannot be empty.")
                continue
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                self.stderr.write("  Passwords do not match.")
                continue
            break

        # Validate uniqueness
        if User.objects.filter(username=username).exists():
            self.stderr.write(self.style.ERROR(f"Username '{username}' already exists."))
            return

        if phone and User.objects.filter(phone=phone).exists():
            self.stderr.write(self.style.ERROR(f"Phone '{phone}' already exists."))
            return

        if telegram_id and User.objects.filter(telegram_id=telegram_id).exists():
            self.stderr.write(self.style.ERROR(f"Telegram ID '{telegram_id}' already exists."))
            return

        # Create user
        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            telegram_id=telegram_id,
            role=role,
            language=language,
            is_active=True,
        )
        user.set_password(password)

        # Sync permissions
        self._sync_permissions(role)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"  User created: {first_name} ({role})"))
        self.stdout.write(f"  ID:          {user.id}")
        self.stdout.write(f"  Username:    {username}")
        self.stdout.write(f"  Phone:       {phone or '—'}")
        self.stdout.write(f"  Telegram:    {telegram_id or '—'}")
        self.stdout.write("")

    def _ask(self, label, required=False, default=""):
        suffix = "" if required else f" [{default}]"
        while True:
            value = input(f"  {label}{suffix}: ").strip()
            if not value:
                if required:
                    self.stderr.write(f"  {label} is required.")
                    continue
                return default
            return value

    def _ask_choice(self, label, choices, default=None):
        display = "/".join(
            f"[{c}]" if c == default else c for c in choices
        )
        while True:
            value = input(f"  {label} ({display}): ").strip().lower()
            if not value and default:
                return default
            if value in choices:
                return value
            self.stderr.write(f"  Must be one of: {', '.join(choices)}")

    def _sync_permissions(self, role):
        """Ensure permissions and role assignments exist."""
        from base.permissions import ALL_PERMISSIONS

        for codename in ALL_PERMISSIONS:
            Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    "name": codename.replace("_", " ").title(),
                    "group": codename.split("_")[0],
                },
            )

        codenames = DEFAULT_ROLE_PERMISSIONS.get(role, set())
        for codename in codenames:
            perm = Permission.objects.get(codename=codename)
            RolePermission.objects.get_or_create(role=role, permission=perm)
