import json

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from base.interfaces.user import IUserRepository
from base.interfaces.session import ISessionRepository
from base.exceptions import AuthenticationError, ValidationError
from base.models import User
from base.sms import normalize_phone, send_otp, verify_otp
from customer.dto.auth import RegisterDTO, SessionDTO
from customer.dto.profile import UpdateProfileDTO


VALID_LANGUAGES = {c[0] for c in User.Language.choices}
PENDING_REG_TTL = getattr(settings, "OTP_EXPIRY_SECONDS", 120)


def _pending_key(phone: str) -> str:
    return f"pending_reg:{phone}"


def _login_key(phone: str) -> str:
    return f"pending_login:{phone}"


def _phone_change_key(user_id: int) -> str:
    return f"pending_phone_change:{user_id}"


class CustomerAuthService:

    def __init__(self, user_repo: IUserRepository, session_repo: ISessionRepository):
        self._users = user_repo
        self._sessions = session_repo

    # ── Registration (OTP) ──────────────────────────────────────────

    def register(self, dto: RegisterDTO) -> dict:
        if not dto.phone or not dto.first_name:
            raise ValidationError("phone and first_name are required")

        if dto.language and dto.language not in VALID_LANGUAGES:
            raise ValidationError(f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")

        phone = normalize_phone(dto.phone)
        if not phone:
            raise ValidationError("Invalid phone number")

        if self._users.get_by_phone(phone):
            raise ValidationError("Phone number already registered")

        if dto.telegram_id and self._users.get_by_telegram_id(dto.telegram_id):
            raise ValidationError("Telegram account already registered")

        sms_result = send_otp(phone)
        if not sms_result["sent"]:
            raise ValidationError(sms_result["message"])

        pending = {
            "phone": phone,
            "first_name": dto.first_name,
            "last_name": dto.last_name,
            "language": dto.language or "uz",
            "telegram_id": dto.telegram_id,
        }
        cache.set(_pending_key(phone), json.dumps(pending), timeout=PENDING_REG_TTL)

        return {
            "message": "Verification code sent",
            "phone": phone,
            "verification_sent": True,
            "expires_in": sms_result.get("expires_in", PENDING_REG_TTL),
        }

    @transaction.atomic
    def verify_register(self, phone: str, code: str, session_info: SessionDTO) -> dict:
        if not phone or not code:
            raise ValidationError("phone and code are required")

        phone = normalize_phone(phone)

        if not verify_otp(phone, code):
            raise ValidationError("Invalid or expired verification code")

        raw = cache.get(_pending_key(phone))
        if not raw:
            raise ValidationError("Registration expired. Please register again.")

        pending = json.loads(raw)
        cache.delete(_pending_key(phone))

        if self._users.get_by_phone(phone):
            raise ValidationError("Phone number already registered")

        user = self._users.create(
            phone=pending["phone"],
            first_name=pending["first_name"],
            last_name=pending["last_name"],
            role=User.Role.CLIENT,
            language=pending["language"],
            telegram_id=pending.get("telegram_id"),
            is_phone_verified=True,
        )

        session = self._sessions.create_session(
            user=user,
            ip=session_info.ip_address,
            ua=session_info.user_agent,
            device=session_info.device,
            hours=720,
        )

        return {
            "session_key": session.key,
            "user": self._user_dict(user),
            "expires_at": session.expires_at.isoformat(),
        }

    def resend_register_code(self, phone: str) -> dict:
        if not phone:
            raise ValidationError("phone is required")

        phone = normalize_phone(phone)

        raw = cache.get(_pending_key(phone))
        if not raw:
            raise ValidationError("No pending registration for this phone. Please register again.")

        result = send_otp(phone)
        if not result["sent"]:
            raise ValidationError(result["message"])

        cache.set(_pending_key(phone), raw, timeout=PENDING_REG_TTL)

        return {"message": result["message"], "expires_in": result.get("expires_in", PENDING_REG_TTL)}

    # ── Login (OTP) ─────────────────────────────────────────────────

    def login(self, phone: str) -> dict:
        if not phone:
            raise ValidationError("phone is required")

        phone = normalize_phone(phone)

        user = self._users.get_by_phone(phone)
        eligible = bool(user and user.role == User.Role.CLIENT and user.is_active)

        if eligible:
            sms_result = send_otp(phone)
            if sms_result["sent"]:
                cache.set(_login_key(phone), phone, timeout=PENDING_REG_TTL)

        return {
            "message": "If an account exists for this phone, a verification code has been sent",
            "phone": phone,
            "expires_in": PENDING_REG_TTL,
        }

    def verify_login(self, phone: str, code: str, session_info: SessionDTO) -> dict:
        if not phone or not code:
            raise ValidationError("phone and code are required")

        phone = normalize_phone(phone)

        if not cache.get(_login_key(phone)):
            raise ValidationError("No pending login for this phone. Please request a code first.")

        if not verify_otp(phone, code):
            raise ValidationError("Invalid or expired verification code")

        cache.delete(_login_key(phone))

        user = self._users.get_by_phone(phone)
        if not user or user.role != User.Role.CLIENT:
            raise AuthenticationError("No account found with this phone number")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        self._users.update_last_seen(user)

        session = self._sessions.create_session(
            user=user,
            ip=session_info.ip_address,
            ua=session_info.user_agent,
            device=session_info.device,
            hours=720,
        )

        return {
            "session_key": session.key,
            "user": self._user_dict(user),
            "expires_at": session.expires_at.isoformat(),
        }

    def resend_login_code(self, phone: str) -> dict:
        if not phone:
            raise ValidationError("phone is required")

        phone = normalize_phone(phone)

        if not cache.get(_login_key(phone)):
            raise ValidationError("No pending login for this phone. Please request a code first.")

        result = send_otp(phone)
        if not result["sent"]:
            raise ValidationError(result["message"])

        cache.set(_login_key(phone), phone, timeout=PENDING_REG_TTL)

        return {"message": result["message"], "expires_in": result.get("expires_in", PENDING_REG_TTL)}

    # ── Session ─────────────────────────────────────────────────────

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

    # ── Profile ─────────────────────────────────────────────────────

    def get_profile(self, user) -> dict:
        return self._user_dict(user)

    def update_profile(self, user, dto: UpdateProfileDTO) -> dict:
        data = dto.to_dict()

        if "language" in data and data["language"] not in VALID_LANGUAGES:
            raise ValidationError(f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")

        if data:
            self._users.update(user, **data)

        return self._user_dict(user)

    # ── Phone change (OTP-protected) ────────────────────────────────

    def request_phone_change(self, user, new_phone: str) -> dict:
        if not new_phone:
            raise ValidationError("new_phone is required")

        new_phone = normalize_phone(new_phone)
        if not new_phone:
            raise ValidationError("Invalid phone number")

        if new_phone == user.phone:
            raise ValidationError("New phone is the same as current")

        if self._users.get_by_phone(new_phone):
            raise ValidationError("Phone number already in use")

        sms_result = send_otp(new_phone)
        if not sms_result["sent"]:
            raise ValidationError(sms_result["message"])

        cache.set(_phone_change_key(user.id), new_phone, timeout=PENDING_REG_TTL)

        return {
            "message": "Verification code sent to new phone",
            "expires_in": sms_result.get("expires_in", PENDING_REG_TTL),
        }

    @transaction.atomic
    def verify_phone_change(self, user, code: str) -> dict:
        if not code:
            raise ValidationError("code is required")

        new_phone = cache.get(_phone_change_key(user.id))
        if not new_phone:
            raise ValidationError("No pending phone change. Please request a code first.")

        if not verify_otp(new_phone, code):
            raise ValidationError("Invalid or expired verification code")

        cache.delete(_phone_change_key(user.id))

        if self._users.get_by_phone(new_phone):
            raise ValidationError("Phone number already in use")

        self._users.update(user, phone=new_phone)
        self._sessions.invalidate_all_for_user(user)

        return {"message": "Phone number updated. Please log in again."}

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
