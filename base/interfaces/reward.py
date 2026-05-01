from abc import abstractmethod
from typing import Optional

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import ReferralReward, UserReward


class IReferralRewardRepository(IBaseRepository[ReferralReward]):

    @abstractmethod
    def get_active(self) -> Optional[ReferralReward]: ...

    @abstractmethod
    def activate(self, reward: ReferralReward) -> ReferralReward: ...

    @abstractmethod
    def deactivate(self, reward: ReferralReward) -> ReferralReward: ...

    @abstractmethod
    def deactivate_all(self) -> int: ...


class IUserRewardRepository(IBaseRepository[UserReward]):

    @abstractmethod
    def get_active_for_user(self, user_id: int) -> QuerySet[UserReward]: ...

    @abstractmethod
    def get_by_type(self, user_id: int, reward_type: str) -> QuerySet[UserReward]: ...

    @abstractmethod
    def get_unused_free_delivery(self, user_id: int) -> Optional[UserReward]: ...

    @abstractmethod
    def get_unclaimed_bonus(self, user_id: int) -> Optional[UserReward]: ...
