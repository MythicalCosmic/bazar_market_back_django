from base.interfaces.user import IUserRepository
from base.interfaces.session import ISessionRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.user import CreateUserDTO, UpdateUserDTO
from base.models import User

STAFF_ROLES = {User.Role.ADMIN, User.Role.MANAGER, User.Role.COURIER}


class UserService:
    def __init__(self, user_repository: IUserRepository, session_repository: ISessionRepository):
        self.user_repository = user_repository
        self.session_repository = session_repository

    def _staff_qs(self):
        return self.user_repository.get_all().filter(role__in=STAFF_ROLES)

    def get_all(self, query=None, role=None, is_active=None, order_by="-created_at", page=1, per_page=20):
        qs = self._staff_qs()
        qs = self.user_repository.search(qs, query, ["first_name", "last_name", "username", "phone"])
        qs = self.user_repository.apply_filters(qs, {"role": role, "is_active": is_active})
        qs = self.user_repository.apply_ordering(qs, order_by, {"created_at", "first_name", "last_name", "role"})
        return self.user_repository.paginate(qs, page, per_page)

    def get_by_id(self, user_id: int) -> User | None:
        return self._staff_qs().filter(pk=user_id).first()

    def get_by_username(self, username: str) -> User | None:
        return self.user_repository.get_by_username(username)

    def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return self.user_repository.get_by_telegram_id(telegram_id)

    def get_by_phone(self, phone: str) -> User | None:
        return self.user_repository.get_by_phone(phone)

    def create_user(self, dto: CreateUserDTO) -> dict:
        if dto.role not in STAFF_ROLES:
            raise ValidationError(f"Role must be one of: {', '.join(STAFF_ROLES)}")
        if self.user_repository.exists(username=dto.username):
            raise ValidationError("Username already exists")
        if dto.phone and self.user_repository.exists(phone=dto.phone):
            raise ValidationError("Phone already exists")

        user = self.user_repository.create(
            username=dto.username,
            phone=dto.phone,
            first_name=dto.first_name,
            last_name=dto.last_name,
            role=dto.role,
            language=dto.language or "uz",
            telegram_id=dto.telegram_id,
        )

        user.set_password(dto.password)

        return {"id": user.id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name}


    def update_user(self, user_id, dto: UpdateUserDTO) -> dict:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        data = dto.to_dict()

        raw_password = data.pop("password", None)

        if "username" in data and data["username"] != user.username:
            if self.user_repository.exists(username=dto.username):
                raise ValidationError("Username already exists")

        if data:
            self.user_repository.update(user, **data)
        if raw_password:
            user.set_password(raw_password)

        return {"id": user.id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name}


    def delete_user(self, user_id: int) -> dict:
        user = self._staff_qs().filter(pk=user_id).first()
        if not user:
            raise NotFoundError("User not found")

        self.user_repository.soft_delete(user)
        self.session_repository.invalidate_all_for_user(user)

        return {"message": "User deleted successfully"}

    def restore_user(self, user_id: int) -> dict:
        user = self.user_repository.get_only_deleted().filter(pk=user_id, role__in=STAFF_ROLES).first()
        if not user:
            raise NotFoundError("User not found or not deleted")

        self.user_repository.restore(user)

        return {"message": "User restored successfully"}