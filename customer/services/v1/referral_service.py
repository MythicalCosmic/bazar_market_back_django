from decimal import Decimal

from base.interfaces.referral import IReferralRepository
from base.interfaces.user import IUserRepository
from base.interfaces.setting import ISettingRepository
from base.exceptions import NotFoundError, ValidationError
from base.models import User


class CustomerReferralService:
    def __init__(
        self,
        referral_repository: IReferralRepository,
        user_repository: IUserRepository,
        setting_repository: ISettingRepository,
    ):
        self.referral_repo = referral_repository
        self.user_repo = user_repository
        self.setting_repo = setting_repository

    def get_my_referral(self, user) -> dict:
        code = str(user.uuid)[:8].upper()
        count = self.referral_repo.get_referral_count(user.id)
        rewards = self.referral_repo.get_total_rewards(user.id)
        return {
            "referral_code": code,
            "referral_link": f"https://t.me/BazarMarketBot?start=ref_{code}",
            "total_referrals": count,
            "total_rewards": str(rewards.get("total") or 0),
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

        reward = Decimal(str(self.setting_repo.get_value("referral_reward", "0")))
        self.referral_repo.create(
            referrer_id=referrer.id,
            referred_id=referred_user_id,
            reward_amount=reward,
            is_rewarded=False,
        )
        return {"message": "Referral applied successfully"}
