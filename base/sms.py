import logging
import random
import string

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

OTP_LENGTH = getattr(settings, "OTP_LENGTH", 6)
OTP_EXPIRY = getattr(settings, "OTP_EXPIRY_SECONDS", 120)
COOLDOWN = 60  # seconds between resends


def _cache_key(phone: str) -> str:
    return f"otp:{phone}"


def _cooldown_key(phone: str) -> str:
    return f"otp_cd:{phone}"


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def send_otp(phone: str) -> dict:
    """Generate OTP, store in cache, send via DevSMS. Returns result dict."""
    # Cooldown check
    if cache.get(_cooldown_key(phone)):
        return {"sent": False, "message": "Please wait before requesting another code", "retry_after": COOLDOWN}

    code = generate_otp()
    cache.set(_cache_key(phone), code, timeout=OTP_EXPIRY)
    cache.set(_cooldown_key(phone), True, timeout=COOLDOWN)

    try:
        message = f"Bazar market ilovasi uchun tasdiqlash kodingiz: {code}. Kod 2 daqiqa amal qiladi."
        resp = requests.post(
            settings.DEVSMS_URL,
            json={
                "phone": phone,
                "text": message,
                "shablon_id": 313,
            },
            headers={
                "Authorization": f"Bearer {settings.DEVSMS_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("success"):
            logger.info(f"OTP sent to {phone}")
            return {"sent": True, "message": "Verification code sent", "expires_in": OTP_EXPIRY}
        else:
            logger.error(f"DevSMS error for {phone}: {data}")
            return {"sent": False, "message": "Failed to send SMS. Please try again."}
    except requests.RequestException as exc:
        logger.error(f"DevSMS request failed for {phone}: {exc}")
        return {"sent": False, "message": "SMS service unavailable. Please try again."}


def verify_otp(phone: str, code: str) -> bool:
    """Check OTP against cached value. Deletes on success."""
    stored = cache.get(_cache_key(phone))
    if not stored:
        return False
    if stored != code:
        return False
    cache.delete(_cache_key(phone))
    cache.delete(_cooldown_key(phone))
    return True
