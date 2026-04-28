import uuid as uuid_lib
from decimal import Decimal

from django.utils import timezone

from base.interfaces.referral import IReferralRepository
from base.interfaces.user import IUserRepository
from base.interfaces.setting import ISettingRepository
from base.interfaces.coupon import ICouponRepository
from base.exceptions import ValidationError
from base.models import User


# Admin-configurable settings keys and their defaults
SETTING_DEFAULTS = {
    "referral_reward_type": "percent",       # "percent" or "fixed"
    "referral_reward_value": "10",           # 10% or 10000 UZS
    "referral_reward_max_discount": "",       # cap for percent, empty = no cap
    "referral_reward_min_order": "",          # minimum order to use, empty = none
    "referral_reward_expires_days": "30",     # coupon valid for N days, 0 = no expiry
}


class CustomerReferralService:
    def __init__(
        self,
        referral_repository: IReferralRepository,
        user_repository: IUserRepository,
        setting_repository: ISettingRepository,
        coupon_repository: ICouponRepository,
    ):
        self.referral_repo = referral_repository
        self.user_repo = user_repository
        self.setting_repo = setting_repository
        self.coupon_repo = coupon_repository

    def get_my_referral(self, user) -> dict:
        code = str(user.uuid)[:8].upper()
        count = self.referral_repo.get_referral_count(user.id)
        rewards = self.referral_repo.get_total_rewards(user.id)

        # Show current reward config so user knows what they'll get
        reward_type = self._setting("referral_reward_type")
        reward_value = self._setting("referral_reward_value")

        return {
            "referral_code": code,
            "referral_link": f"https://t.me/{self._get_bot_username()}?start=ref_{code}",
            "total_referrals": count,
            "total_rewards": str(rewards.get("total") or 0),
            "reward_info": {
                "type": reward_type,
                "value": reward_value,
            },
        }

    def list_my_referrals(self, user_id: int, page=1, per_page=20):
        qs = self.referral_repo.get_by_referrer(user_id).select_related("referred").order_by("-created_at")
        return self.referral_repo.paginate(qs, page, per_page)

    def apply_referral(self, referred_user_id: int, referral_code: str) -> dict:
        if self.referral_repo.has_been_referred(referred_user_id):
            raise ValidationError("You have already been referred")

        referrer = User.objects.filter(
            uuid__startswith=referral_code.lower(),
            role=User.Role.CLIENT,
            is_active=True,
            deleted_at__isnull=True,
        ).first()
        if not referrer:
            raise ValidationError("Invalid referral code")
        if referrer.id == referred_user_id:
            raise ValidationError("Cannot refer yourself")

        reward_value = Decimal(self._setting("referral_reward_value") or "0")
        self.referral_repo.create(
            referrer_id=referrer.id,
            referred_id=referred_user_id,
            reward_amount=reward_value,
            is_rewarded=False,
        )
        return {"message": "Referral applied successfully"}

    def grant_reward_on_first_order(self, user_id: int):
        """Called after a user's first completed order.
        Creates a coupon for the referrer if this user was referred."""
        referral = self.referral_repo.get_by_referred(user_id)
        if not referral or referral.is_rewarded:
            return

        reward_type = self._setting("referral_reward_type")
        reward_value = self._setting("referral_reward_value")

        if not reward_value or Decimal(reward_value) <= 0:
            return

        # Build coupon for the referrer
        code = f"REF-{uuid_lib.uuid4().hex[:8].upper()}"
        expires_days = int(self._setting("referral_reward_expires_days") or "30")
        max_discount_raw = self._setting("referral_reward_max_discount")
        min_order_raw = self._setting("referral_reward_min_order")

        kwargs = {
            "code": code,
            "type": reward_type,
            "value": Decimal(reward_value),
            "usage_limit": 1,
            "per_user_limit": 1,
            "is_active": True,
        }

        if max_discount_raw:
            kwargs["max_discount"] = Decimal(max_discount_raw)
        if min_order_raw:
            kwargs["min_order"] = Decimal(min_order_raw)
        if expires_days > 0:
            kwargs["expires_at"] = timezone.now() + timezone.timedelta(days=expires_days)

        self.coupon_repo.create(**kwargs)

        # Mark referral as rewarded
        self.referral_repo.mark_rewarded(referral)
        referral.reward_amount = Decimal(reward_value)
        referral.save(update_fields=["reward_amount"])

        # Send notification to referrer
        try:
            from base.models import Notification
            referrer = self.user_repo.get_by_id(referral.referrer_id)
            referred = self.user_repo.get_by_id(user_id)
            if referrer:
                Notification.objects.create(
                    user_id=referrer.id,
                    type="promo",
                    title="Referral reward!",
                    body=f"Your friend {referred.first_name} placed their first order! "
                         f"Use code {code} for your reward.",
                    channel="telegram",
                    payload={"coupon_code": code},
                )
                # Also send via Telegram
                from bot.notify import notify_referral_reward
                notify_referral_reward(referrer, code)
        except Exception:
            pass

    def _get_bot_username(self) -> str:
        return str(self.setting_repo.get_value("bot_username", "BazarMarketBot"))

    def _setting(self, key: str) -> str:
        default = SETTING_DEFAULTS.get(key, "")
        return str(self.setting_repo.get_value(key, default))
