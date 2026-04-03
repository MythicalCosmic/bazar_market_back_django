from base.interfaces.permission import (
    IPermissionRepository,
    IRolePermissionRepository,
    IUserPermissionRepository,
)
from base.interfaces.user import IUserRepository
from base.exceptions import NotFoundError, ValidationError
from base.models import User
from base.permissions import ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS


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

    def set_role_permissions(self, role: str, codenames: list[str]) -> dict:
        if role not in dict(User.Role.choices):
            raise ValidationError(f"Invalid role: {role}")
        if role == "admin":
            raise ValidationError("Cannot modify admin permissions")

        valid = self.perm_repo.get_all_codenames()
        invalid = set(codenames) - valid
        if invalid:
            raise ValidationError(f"Unknown permissions: {', '.join(invalid)}")

        self.role_perm_repo.sync_role(role, set(codenames))
        return {"message": f"Permissions updated for role '{role}'", "count": len(codenames)}

    def reset_role_to_defaults(self, role: str) -> dict:
        if role not in dict(User.Role.choices):
            raise ValidationError(f"Invalid role: {role}")
        if role == "admin":
            raise ValidationError("Cannot modify admin permissions")

        defaults = DEFAULT_ROLE_PERMISSIONS.get(role, set())
        self.role_perm_repo.sync_role(role, defaults)
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

    def grant_user_permission(self, user_id: int, codename: str) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        perm = self.perm_repo.get_by_codename(codename)
        if not perm:
            raise ValidationError(f"Unknown permission: {codename}")

        self.user_perm_repo.grant(user_id, perm)
        return {"message": f"Permission '{codename}' granted to user {user_id}"}

    def deny_user_permission(self, user_id: int, codename: str) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        perm = self.perm_repo.get_by_codename(codename)
        if not perm:
            raise ValidationError(f"Unknown permission: {codename}")

        self.user_perm_repo.deny(user_id, perm)
        return {"message": f"Permission '{codename}' denied for user {user_id}"}

    def remove_user_permission(self, user_id: int, codename: str) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        perm = self.perm_repo.get_by_codename(codename)
        if not perm:
            raise ValidationError(f"Unknown permission: {codename}")

        removed = self.user_perm_repo.remove(user_id, perm)
        if not removed:
            raise NotFoundError("Override not found")
        return {"message": f"Permission override removed for user {user_id}"}

    def clear_user_permissions(self, user_id: int) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        count = self.user_perm_repo.clear_for_user(user_id)
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
