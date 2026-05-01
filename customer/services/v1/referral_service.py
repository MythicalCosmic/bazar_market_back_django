import uuid as uuid_lib
from decimal import Decimal

from django.utils import timezone

from base.interfaces.referral import IReferralRepository
from base.interfaces.reward import IReferralRewardRepository, IUserRewardRepository
from base.interfaces.user import IUserRepository
from base.interfaces.setting import ISettingRepository
from base.interfaces.coupon import ICouponRepository
from base.exceptions import ValidationError
from base.models import User


class CustomerReferralService:
    def __init__(
        self,
        referral_repository: IReferralRepository,
        user_repository: IUserRepository,
        setting_repository: ISettingRepository,
        coupon_repository: ICouponRepository,
        referral_reward_repository: IReferralRewardRepository,
        user_reward_repository: IUserRewardRepository,
    ):
        self.referral_repo = referral_repository
        self.user_repo = user_repository
        self.setting_repo = setting_repository
        self.coupon_repo = coupon_repository
        self.reward_repo = referral_reward_repository
        self.user_reward_repo = user_reward_repository

    def get_my_referral(self, user) -> dict:
        code = str(user.uuid)[:8].upper()
        count = self.referral_repo.get_referral_count(user.id)
        rewards = self.referral_repo.get_total_rewards(user.id)

        active_reward = self.reward_repo.get_active()
        reward_info = None
        if active_reward:
            reward_info = {"type": active_reward.type, "name": active_reward.name}

        webapp_url = str(self.setting_repo.get_value("webapp_url", ""))
        if not webapp_url:
            webapp_url = "https://app.example.com"

        return {
            "referral_code": code,
            "referral_link": f"{webapp_url.rstrip('/')}?ref={code}",
            "total_referrals": count,
            "total_rewards": str(rewards.get("total") or 0),
            "reward_info": reward_info,
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

        self.referral_repo.create(
            referrer_id=referrer.id,
            referred_id=referred_user_id,
            reward_amount=Decimal(0),
            is_rewarded=False,
        )
        return {"message": "Referral applied successfully"}

    def grant_reward_on_first_order(self, user_id: int):
        """Called after a referred user's first completed order.
        Grants the active ReferralReward to the referrer."""
        referral = self.referral_repo.get_by_referred(user_id)
        if not referral or referral.is_rewarded:
            return

        active_reward = self.reward_repo.get_active()
        if not active_reward:
            return

        referrer_id = referral.referrer_id

        expires_at = None
        if active_reward.type == "coupon":
            self._grant_coupon(referrer_id, active_reward, referral)
        elif active_reward.type == "free_delivery":
            if active_reward.coupon_expires_days and active_reward.coupon_expires_days > 0:
                expires_at = timezone.now() + timezone.timedelta(days=active_reward.coupon_expires_days)
            self.user_reward_repo.create(
                user_id=referrer_id,
                reward=active_reward,
                referral=referral,
                type="free_delivery",
                free_deliveries_remaining=active_reward.free_delivery_count,
                expires_at=expires_at,
            )
        elif active_reward.type == "bonus_product":
            if not active_reward.bonus_product:
                return
            if active_reward.coupon_expires_days and active_reward.coupon_expires_days > 0:
                expires_at = timezone.now() + timezone.timedelta(days=active_reward.coupon_expires_days)
            self.user_reward_repo.create(
                user_id=referrer_id,
                reward=active_reward,
                referral=referral,
                type="bonus_product",
                bonus_product=active_reward.bonus_product,
                bonus_quantity=active_reward.bonus_quantity,
                expires_at=expires_at,
            )

        # Mark referral as rewarded
        self.referral_repo.mark_rewarded(referral)

        # Notify referrer
        self._notify_referrer(referral, active_reward, user_id)

    def _grant_coupon(self, referrer_id, reward, referral):
        if not reward.coupon_value or reward.coupon_value <= 0:
            return

        code = f"REF-{uuid_lib.uuid4().hex[:8].upper()}"

        kwargs = {
            "code": code,
            "type": reward.coupon_type,
            "value": reward.coupon_value,
            "usage_limit": 1,
            "per_user_limit": 1,
            "is_active": True,
        }
        if reward.coupon_max_discount:
            kwargs["max_discount"] = reward.coupon_max_discount
        if reward.coupon_min_order:
            kwargs["min_order"] = reward.coupon_min_order
        if reward.coupon_expires_days and reward.coupon_expires_days > 0:
            kwargs["expires_at"] = timezone.now() + timezone.timedelta(days=reward.coupon_expires_days)

        coupon = self.coupon_repo.create(**kwargs)

        self.user_reward_repo.create(
            user_id=referrer_id,
            reward=reward,
            referral=referral,
            type="coupon",
            coupon=coupon,
            expires_at=kwargs.get("expires_at"),
        )

        referral.reward_amount = reward.coupon_value
        referral.save(update_fields=["reward_amount"])

    def _notify_referrer(self, referral, reward, referred_user_id):
        try:
            from base.models import Notification
            referrer = self.user_repo.get_by_id(referral.referrer_id)
            referred = self.user_repo.get_by_id(referred_user_id)
            if not referrer or not referred:
                return

            body_map = {
                "coupon": f"Your friend {referred.first_name} placed their first order! You got a discount coupon.",
                "free_delivery": f"Your friend {referred.first_name} placed their first order! You got {reward.free_delivery_count} free delivery order(s).",
                "bonus_product": f"Your friend {referred.first_name} placed their first order! You got a free product on your next order.",
            }

            Notification.objects.create(
                user_id=referrer.id,
                type="promo",
                title="Referral reward!",
                body=body_map.get(reward.type, "You received a referral reward!"),
                channel="push",
                payload={"reward_type": reward.type},
            )
        except Exception:
            pass
