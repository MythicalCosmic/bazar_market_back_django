from abc import abstractmethod

from django.db.models import QuerySet

from base.interfaces.base import IBaseRepository
from base.models import Banner


class IBannerRepository(IBaseRepository[Banner]):

    @abstractmethod
    def get_active(self) -> QuerySet[Banner]: ...

    @abstractmethod
    def get_current(self) -> QuerySet[Banner]: ...

    @abstractmethod
    def deactivate(self, banner: Banner) -> Banner: ...

    @abstractmethod
    def activate(self, banner: Banner) -> Banner: ...

    @abstractmethod
    def reorder(self, banner_ids: list[int]) -> None: ...
