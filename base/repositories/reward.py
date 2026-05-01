from typing import Optional

from django.db.models import QuerySet

from base.models import ReferralReward, UserReward
from base.repositories.base import BaseRepository


class ReferralRewardRepository(BaseRepository[ReferralReward]):
    model = ReferralReward

    def get_active(self) -> Optional[ReferralReward]:
        return self.get_queryset().filter(is_active=True).first()

    def activate(self, reward: ReferralReward) -> ReferralReward:
        self.deactivate_all()
        return self.update(reward, is_active=True)

    def deactivate(self, reward: ReferralReward) -> ReferralReward:
        return self.update(reward, is_active=False)

    def deactivate_all(self) -> int:
        return self.model.objects.filter(is_active=True).update(is_active=False)


class UserRewardRepository(BaseRepository[UserReward]):
    model = UserReward

    def get_active_for_user(self, user_id: int) -> QuerySet[UserReward]:
        return self.get_queryset().filter(user_id=user_id, is_used=False)

    def get_by_type(self, user_id: int, reward_type: str) -> QuerySet[UserReward]:
        return self.get_active_for_user(user_id).filter(type=reward_type)

    def get_unused_free_delivery(self, user_id: int) -> Optional[UserReward]:
        return self.get_by_type(user_id, "free_delivery").filter(
            free_deliveries_remaining__gt=0,
        ).first()

    def get_unclaimed_bonus(self, user_id: int) -> Optional[UserReward]:
        return self.get_by_type(user_id, "bonus_product").filter(
            bonus_claimed=False, bonus_product__isnull=False,
        ).select_related("bonus_product").first()
