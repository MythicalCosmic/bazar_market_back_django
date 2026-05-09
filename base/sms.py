import hmac
import logging
import random
import string

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

OTP_LENGTH = getattr(settings, "OTP_LENGTH", 6)
OTP_EXPIRY = getattr(settings, "OTP_EXPIRY_SECONDS", 120)
COOLDOWN = 60
MAX_ATTEMPTS = getattr(settings, "OTP_MAX_ATTEMPTS", 5)


def _cache_key(phone: str) -> str:
    return f"otp:{phone}"


def _cooldown_key(phone: str) -> str:
    return f"otp_cd:{phone}"


def _attempts_key(phone: str) -> str:
    return f"otp_attempts:{phone}"


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def send_otp(phone: str) -> dict:
    """Generate OTP, send via DevSMS, persist on success only."""
    if cache.get(_cooldown_key(phone)):
        return {"sent": False, "message": "Please wait before requesting another code", "retry_after": COOLDOWN}

    code = generate_otp()
    message = f"Bazar market ilovasi uchun tasdiqlash kodingiz: {code}. Kod 2 daqiqa amal qiladi."

    try:
        resp = requests.post(
            settings.DEVSMS_URL,
            json={
                "phone": phone,
                "message": message,
                "shablon_id": 313,
            },
            headers={
                "Authorization": f"Bearer {settings.DEVSMS_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        data = resp.json() if resp.content else {}
    except requests.RequestException as exc:
        logger.error(f"DevSMS request failed for {phone}: {exc}")
        return {"sent": False, "message": "SMS service unavailable. Please try again."}

    if resp.status_code != 200 or not data.get("success"):
        logger.error(f"DevSMS error for {phone}: status={resp.status_code} body={data}")
        return {"sent": False, "message": "Failed to send SMS. Please try again."}

    cache.set(_cache_key(phone), code, timeout=OTP_EXPIRY)
    cache.set(_cooldown_key(phone), True, timeout=COOLDOWN)
    cache.delete(_attempts_key(phone))
    logger.info(f"OTP sent to {phone}")
    return {"sent": True, "message": "Verification code sent", "expires_in": OTP_EXPIRY}


def verify_otp(phone: str, code: str) -> bool:
    """Verify OTP with constant-time compare and per-phone attempt limit."""
    stored = cache.get(_cache_key(phone))
    if not stored:
        return False

    try:
        attempts = cache.incr(_attempts_key(phone))
    except ValueError:
        cache.set(_attempts_key(phone), 1, timeout=OTP_EXPIRY)
        attempts = 1

    if attempts > MAX_ATTEMPTS:
        cache.delete(_cache_key(phone))
        cache.delete(_attempts_key(phone))
        return False

    if not hmac.compare_digest(str(stored), str(code)):
        return False

    cache.delete(_cache_key(phone))
    cache.delete(_cooldown_key(phone))
    cache.delete(_attempts_key(phone))
    return True
