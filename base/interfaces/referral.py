from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import Referral


class IReferralRepository(IBaseRepository[Referral]):

    @abstractmethod
    def get_by_referrer(self, referrer_id: int) -> QuerySet[Referral]: ...

    @abstractmethod
    def get_by_referred(self, referred_id: int) -> Optional[Referral]: ...

    @abstractmethod
    def has_been_referred(self, user_id: int) -> bool: ...

    @abstractmethod
    def mark_rewarded(self, referral: Referral) -> Referral: ...

    @abstractmethod
    def get_unrewarded(self, referrer_id: int) -> QuerySet[Referral]: ...

    @abstractmethod
    def get_referral_count(self, referrer_id: int) -> int: ...

    @abstractmethod
    def get_total_rewards(self, referrer_id: int) -> dict: ...
