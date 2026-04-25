from django.db import transaction

from base.interfaces.user import IUserRepository
from base.interfaces.session import ISessionRepository
from base.exceptions import AuthenticationError, ValidationError
from base.models import User
from base.sms import send_otp, verify_otp
from customer.dto.auth import RegisterDTO, LoginDTO, SessionDTO
from customer.dto.profile import UpdateProfileDTO


VALID_LANGUAGES = {c[0] for c in User.Language.choices}


class CustomerAuthService:

    def __init__(self, user_repo: IUserRepository, session_repo: ISessionRepository):
        self._users = user_repo
        self._sessions = session_repo

    @transaction.atomic
    def register(self, dto: RegisterDTO, session_info: SessionDTO) -> dict:
        if not dto.phone or not dto.first_name or not dto.password:
            raise ValidationError("phone, first_name, and password are required")

        if len(dto.password) < 6:
            raise ValidationError("Password must be at least 6 characters")

        if dto.language and dto.language not in VALID_LANGUAGES:
            raise ValidationError(f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")

        if self._users.get_by_phone(dto.phone):
            raise ValidationError("Phone number already registered")

        if dto.telegram_id and self._users.get_by_telegram_id(dto.telegram_id):
            raise ValidationError("Telegram account already registered")

        user = self._users.create(
            phone=dto.phone,
            first_name=dto.first_name,
            last_name=dto.last_name,
            role=User.Role.CLIENT,
            language=dto.language or "uz",
            telegram_id=dto.telegram_id,
            is_phone_verified=False,
        )
        user.set_password(dto.password)

        session = self._sessions.create_session(
            user=user,
            ip=session_info.ip_address,
            ua=session_info.user_agent,
            device=session_info.device,
        )

        # Send verification SMS
        sms_result = send_otp(dto.phone)

        return {
            "session_key": session.key,
            "user": self._user_dict(user),
            "expires_at": session.expires_at.isoformat(),
            "verification_sent": sms_result.get("sent", False),
        }

    def verify_phone(self, user, code: str) -> dict:
        if user.is_phone_verified:
            raise ValidationError("Phone is already verified")

        if not code or len(code) != 6:
            raise ValidationError("Invalid verification code")

        if not verify_otp(user.phone, code):
            raise ValidationError("Invalid or expired verification code")

        self._users.update(user, is_phone_verified=True)
        return {"message": "Phone verified successfully", "is_phone_verified": True}

    def resend_code(self, user) -> dict:
        if user.is_phone_verified:
            raise ValidationError("Phone is already verified")

        result = send_otp(user.phone)
        if not result["sent"]:
            raise ValidationError(result["message"])

        return {"message": result["message"], "expires_in": result.get("expires_in", 120)}

    def login(self, dto: LoginDTO, session_info: SessionDTO) -> dict:
        user = self._users.get_by_phone(dto.phone)
        if not user:
            raise AuthenticationError("Invalid phone or password")

        if user.role != User.Role.CLIENT:
            raise AuthenticationError("Invalid phone or password")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        if not user.check_password(dto.password):
            raise AuthenticationError("Invalid phone or password")

        self._users.update_last_seen(user)

        session = self._sessions.create_session(
            user=user,
            ip=session_info.ip_address,
            ua=session_info.user_agent,
            device=session_info.device,
        )

        return {
            "session_key": session.key,
            "user": self._user_dict(user),
            "expires_at": session.expires_at.isoformat(),
        }

    def logout(self, session_token: str) -> dict:
        session = self._sessions.get_by_key(session_token)
        if not session:
            raise AuthenticationError("Invalid or expired session")
        self._sessions.invalidate(session)
        return {"message": "Logged out"}

    def logout_all(self, session_token: str) -> dict:
        session = self._sessions.get_by_key(session_token)
        if not session:
            raise AuthenticationError("Invalid or expired session")
        self._sessions.invalidate_all_for_user(session.user)
        return {"message": "Logged out from all devices"}

    def get_profile(self, user) -> dict:
        return self._user_dict(user)

    def update_profile(self, user, dto: UpdateProfileDTO) -> dict:
        data = dto.to_dict()

        raw_password = data.pop("password", None)

        if "phone" in data and data["phone"] != user.phone:
            if self._users.get_by_phone(data["phone"]):
                raise ValidationError("Phone number already in use")

        if "language" in data and data["language"] not in VALID_LANGUAGES:
            raise ValidationError(f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")

        if data:
            self._users.update(user, **data)

        if raw_password:
            if len(raw_password) < 6:
                raise ValidationError("Password must be at least 6 characters")
            user.set_password(raw_password)

        return self._user_dict(user)

    @transaction.atomic
    def delete_account(self, user) -> dict:
        self._users.soft_delete(user)
        self._sessions.invalidate_all_for_user(user)
        return {"message": "Account deleted"}

    @staticmethod
    def _user_dict(user) -> dict:
        return {
            "id": user.id,
            "uuid": str(user.uuid),
            "phone": user.phone,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language": user.language,
            "is_phone_verified": user.is_phone_verified,
            "created_at": user.created_at.isoformat(),
        }
