from typing import Optional

from django.db.models import QuerySet, Sum

from base.models import Referral
from base.repositories.base import BaseRepository


class ReferralRepository(BaseRepository[Referral]):
    model = Referral

    def get_by_referrer(self, referrer_id: int) -> QuerySet[Referral]:
        return self.get_queryset().filter(referrer_id=referrer_id)

    def get_by_referred(self, referred_id: int) -> Optional[Referral]:
        return self.get_queryset().filter(referred_id=referred_id).first()

    def has_been_referred(self, user_id: int) -> bool:
        return self.exists(referred_id=user_id)

    def mark_rewarded(self, referral: Referral) -> Referral:
        return self.update(referral, is_rewarded=True)

    def get_unrewarded(self, referrer_id: int) -> QuerySet[Referral]:
        return self.get_by_referrer(referrer_id).filter(is_rewarded=False)

    def get_referral_count(self, referrer_id: int) -> int:
        return self.get_by_referrer(referrer_id).count()

    def get_total_rewards(self, referrer_id: int) -> dict:
        return self.get_by_referrer(referrer_id).filter(
            is_rewarded=True
        ).aggregate(total=Sum("reward_amount"))
