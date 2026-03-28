from base.models import Permission, RolePermission, UserPermission
from base.permissions import clear_permission_cache
from base.repositories.base import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    def get_by_codename(self, codename: str):
        return self.get_queryset().filter(codename=codename).first()

    def get_by_group(self, group: str):
        return list(self.get_queryset().filter(group=group))

    def get_all_codenames(self) -> set:
        return set(self.get_queryset().values_list("codename", flat=True))


class RolePermissionRepository(BaseRepository[RolePermission]):
    model = RolePermission

    def get_for_role(self, role: str) -> list:
        return list(
            self.get_queryset()
            .filter(role=role)
            .select_related("permission")
        )

    def get_codenames_for_role(self, role: str) -> set:
        return set(
            self.get_queryset()
            .filter(role=role)
            .values_list("permission__codename", flat=True)
        )

    def assign(self, role: str, permission: Permission) -> RolePermission:
        obj, _ = RolePermission.objects.get_or_create(
            role=role, permission=permission
        )
        clear_permission_cache(role=role)
        return obj

    def revoke(self, role: str, permission: Permission) -> bool:
        count, _ = (
            RolePermission.objects.filter(role=role, permission=permission).delete()
        )
        clear_permission_cache(role=role)
        return count > 0

    def sync_role(self, role: str, codenames: set) -> None:
        RolePermission.objects.filter(role=role).delete()
        perms = Permission.objects.filter(codename__in=codenames)
        RolePermission.objects.bulk_create(
            [RolePermission(role=role, permission=p) for p in perms]
        )
        clear_permission_cache(role=role)


class UserPermissionRepository(BaseRepository[UserPermission]):
    model = UserPermission

    def get_for_user(self, user_id: int) -> list:
        return list(
            self.get_queryset()
            .filter(user_id=user_id)
            .select_related("permission")
        )

    def grant(self, user_id: int, permission: Permission) -> UserPermission:
        obj, created = UserPermission.objects.get_or_create(
            user_id=user_id, permission=permission,
            defaults={"is_granted": True},
        )
        if not created and not obj.is_granted:
            obj.is_granted = True
            obj.save(update_fields=["is_granted"])
        clear_permission_cache(user_id=user_id)
        return obj

    def deny(self, user_id: int, permission: Permission) -> UserPermission:
        obj, created = UserPermission.objects.get_or_create(
            user_id=user_id, permission=permission,
            defaults={"is_granted": False},
        )
        if not created and obj.is_granted:
            obj.is_granted = False
            obj.save(update_fields=["is_granted"])
        clear_permission_cache(user_id=user_id)
        return obj

    def remove(self, user_id: int, permission: Permission) -> bool:
        count, _ = (
            UserPermission.objects.filter(user_id=user_id, permission=permission).delete()
        )
        clear_permission_cache(user_id=user_id)
        return count > 0

    def clear_for_user(self, user_id: int) -> int:
        count, _ = UserPermission.objects.filter(user_id=user_id).delete()
        clear_permission_cache(user_id=user_id)
        return count
