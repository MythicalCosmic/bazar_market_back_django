from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Sequence, Any

from django.db import models
from django.db.models import QuerySet

T = TypeVar("T", bound=models.Model)


class IBaseRepository(ABC, Generic[T]):

    @abstractmethod
    def get_queryset(self) -> QuerySet[T]: ...

    @abstractmethod
    def get_by_id(self, pk: int) -> Optional[T]: ...

    @abstractmethod
    def get_by_ids(self, pks: Sequence[int]) -> QuerySet[T]: ...

    @abstractmethod
    def get_all(self) -> QuerySet[T]: ...

    @abstractmethod
    def filter_by(self, **kwargs: Any) -> QuerySet[T]: ...

    @abstractmethod
    def create(self, **kwargs: Any) -> T: ...

    @abstractmethod
    def bulk_create(self, objects: Sequence[T], **kwargs: Any) -> list[T]: ...

    @abstractmethod
    def update(self, instance: T, **kwargs: Any) -> T: ...

    @abstractmethod
    def bulk_update(self, queryset: QuerySet[T], **kwargs: Any) -> int: ...

    @abstractmethod
    def delete(self, instance: T) -> None: ...

    @abstractmethod
    def delete_by_id(self, pk: int) -> int: ...

    @abstractmethod
    def exists(self, **kwargs: Any) -> bool: ...

    @abstractmethod
    def count(self, **kwargs: Any) -> int: ...

    @abstractmethod
    def first(self, **kwargs: Any) -> Optional[T]: ...

    @abstractmethod
    def last(self, **kwargs: Any) -> Optional[T]: ...

    @abstractmethod
    def get_or_create(
        self, defaults: Optional[dict] = None, **kwargs: Any
    ) -> tuple[T, bool]: ...

    @abstractmethod
    def update_or_create(
        self, defaults: Optional[dict] = None, **kwargs: Any
    ) -> tuple[T, bool]: ...


class ISoftDeleteRepository(IBaseRepository[T]):

    @abstractmethod
    def get_with_deleted(self) -> QuerySet[T]: ...

    @abstractmethod
    def get_only_deleted(self) -> QuerySet[T]: ...

    @abstractmethod
    def soft_delete(self, instance: T) -> T: ...

    @abstractmethod
    def soft_delete_by_id(self, pk: int) -> int: ...

    @abstractmethod
    def bulk_soft_delete(self, queryset: QuerySet[T]) -> int: ...

    @abstractmethod
    def restore(self, instance: T) -> T: ...

    @abstractmethod
    def restore_by_id(self, pk: int) -> int: ...

    @abstractmethod
    def bulk_restore(self, queryset: QuerySet[T]) -> int: ...

    @abstractmethod
    def hard_delete(self, instance: T) -> None: ...

    @abstractmethod
    def hard_delete_by_id(self, pk: int) -> int: ...
