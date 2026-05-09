from django.db import transaction

from base.interfaces.permission import (
    IPermissionRepository,
    IRolePermissionRepository,
    IUserPermissionRepository,
)
from base.interfaces.user import IUserRepository
from base.exceptions import NotFoundError, ValidationError, ForbiddenError
from base.models import User
from base.permissions import (
    ALL_PERMISSIONS,
    DEFAULT_ROLE_PERMISSIONS,
    clear_permission_cache,
)


class RoleService:
    def __init__(
        self,
        permission_repository: IPermissionRepository,
        role_permission_repository: IRolePermissionRepository,
        user_permission_repository: IUserPermissionRepository,
        user_repository: IUserRepository,
    ):
        self.perm_repo = permission_repository
        self.role_perm_repo = role_permission_repository
        self.user_perm_repo = user_permission_repository
        self.user_repo = user_repository

    @staticmethod
    def _guard_user(actor, target):
        """Reject permission mutations on self, on CLIENT users, and on admin users
        when the actor is not an admin."""
        if target.role == User.Role.CLIENT:
            raise ForbiddenError("Cannot assign admin permissions to a customer account")
        if actor is None:
            return
        if target.id == actor.id:
            raise ForbiddenError("You cannot modify your own permissions")
        if target.role == User.Role.ADMIN and actor.role != User.Role.ADMIN:
            raise ForbiddenError("Only an admin can modify an admin user's permissions")

    def list_permissions(self, group: str = None) -> list[dict]:
        qs = self.perm_repo.get_all()
        if group:
            qs = qs.filter(group=group)
        return [
            {"id": p.id, "codename": p.codename, "name": p.name, "group": p.group}
            for p in qs
        ]

    def list_permission_groups(self) -> list[str]:
        return list(
            self.perm_repo.get_all()
            .exclude(group="")
            .values_list("group", flat=True)
            .distinct()
            .order_by("group")
        )

    def get_role_permissions(self, role: str) -> dict:
        if role not in dict(User.Role.choices):
            raise ValidationError(f"Invalid role: {role}")

        items = self.role_perm_repo.get_for_role(role)
        return {
            "role": role,
            "permissions": [
                {
                    "id": rp.permission.id,
                    "codename": rp.permission.codename,
                    "name": rp.permission.name,
                    "group": rp.permission.group,
                }
                for rp in items
            ],
        }

    @transaction.atomic
    def set_role_permissions(self, role: str, codenames: list[str]) -> dict:
        if role not in dict(User.Role.choices):
            raise ValidationError(f"Invalid role: {role}")
        if role == User.Role.ADMIN:
            raise ValidationError("Cannot modify admin permissions")
        if role == User.Role.CLIENT:
            raise ValidationError("Cannot assign admin permissions to the client role")

        valid = self.perm_repo.get_all_codenames()
        invalid = set(codenames) - valid
        if invalid:
            raise ValidationError(f"Unknown permissions: {', '.join(invalid)}")

        self.role_perm_repo.sync_role(role, set(codenames))
        clear_permission_cache(role=role)
        return {"message": f"Permissions updated for role '{role}'", "count": len(codenames)}

    @transaction.atomic
    def reset_role_to_defaults(self, role: str) -> dict:
        if role not in dict(User.Role.choices):
            raise ValidationError(f"Invalid role: {role}")
        if role == User.Role.ADMIN:
            raise ValidationError("Cannot modify admin permissions")
        if role == User.Role.CLIENT:
            raise ValidationError("Cannot assign admin permissions to the client role")

        defaults = DEFAULT_ROLE_PERMISSIONS.get(role, set())
        self.role_perm_repo.sync_role(role, defaults)
        clear_permission_cache(role=role)
        return {"message": f"Role '{role}' reset to defaults", "count": len(defaults)}

    def get_user_permissions(self, user_id: int) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        overrides = self.user_perm_repo.get_for_user(user_id)
        return {
            "user_id": user_id,
            "role": user.role,
            "overrides": [
                {
                    "id": up.permission.id,
                    "codename": up.permission.codename,
                    "name": up.permission.name,
                    "is_granted": up.is_granted,
                }
                for up in overrides
            ],
        }

    @transaction.atomic
    def grant_user_permission(self, user_id: int, codename: str, actor: User | None = None) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        self._guard_user(actor, user)

        perm = self.perm_repo.get_by_codename(codename)
        if not perm:
            raise ValidationError(f"Unknown permission: {codename}")

        self.user_perm_repo.grant(user_id, perm)
        clear_permission_cache(user_id=user_id)
        return {"message": f"Permission '{codename}' granted to user {user_id}"}

    @transaction.atomic
    def deny_user_permission(self, user_id: int, codename: str, actor: User | None = None) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        self._guard_user(actor, user)

        perm = self.perm_repo.get_by_codename(codename)
        if not perm:
            raise ValidationError(f"Unknown permission: {codename}")

        self.user_perm_repo.deny(user_id, perm)
        clear_permission_cache(user_id=user_id)
        return {"message": f"Permission '{codename}' denied for user {user_id}"}

    @transaction.atomic
    def remove_user_permission(self, user_id: int, codename: str, actor: User | None = None) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        self._guard_user(actor, user)

        perm = self.perm_repo.get_by_codename(codename)
        if not perm:
            raise ValidationError(f"Unknown permission: {codename}")

        removed = self.user_perm_repo.remove(user_id, perm)
        if not removed:
            raise NotFoundError("Override not found")
        clear_permission_cache(user_id=user_id)
        return {"message": f"Permission override removed for user {user_id}"}

    @transaction.atomic
    def clear_user_permissions(self, user_id: int, actor: User | None = None) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        self._guard_user(actor, user)

        count = self.user_perm_repo.clear_for_user(user_id)
        clear_permission_cache(user_id=user_id)
        return {"cleared": count}

    def sync_all_permissions(self) -> dict:
        existing = self.perm_repo.get_all_codenames()
        to_create = ALL_PERMISSIONS - existing

        from base.models import Permission
        if to_create:
            self.perm_repo.bulk_create([
                Permission(
                    codename=code,
                    name=code.replace("_", " ").title(),
                    group=code.split("_")[0],
                )
                for code in to_create
            ])

        return {"synced": len(to_create), "total": len(ALL_PERMISSIONS)}
