from typing import TypeVar, Generic, Optional, Sequence, Any

from django.db import models
from django.db.models import QuerySet
from django.utils import timezone

T = TypeVar("T", bound=models.Model)


class BaseRepository(Generic[T]):
    model: type[T]

    def get_queryset(self) -> QuerySet[T]:
        return self.model.objects.all()

    def get_by_id(self, pk: int) -> Optional[T]:
        return self.get_queryset().filter(pk=pk).first()

    def get_by_ids(self, pks: Sequence[int]) -> QuerySet[T]:
        return self.get_queryset().filter(pk__in=pks)

    def get_all(self) -> QuerySet[T]:
        return self.get_queryset()

    def filter_by(self, **kwargs: Any) -> QuerySet[T]:
        return self.get_queryset().filter(**kwargs)

    def create(self, **kwargs: Any) -> T:
        return self.model.objects.create(**kwargs)

    def bulk_create(self, objects: Sequence[T], **kwargs: Any) -> list[T]:
        return self.model.objects.bulk_create(objects, **kwargs)

    def update(self, instance: T, **kwargs: Any) -> T:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        update_fields = list(kwargs.keys())
        for field in self.model._meta.local_fields:
            if getattr(field, "auto_now", False) and field.name not in update_fields:
                update_fields.append(field.name)
        instance.save(update_fields=update_fields)
        return instance

    def bulk_update(self, queryset: QuerySet[T], **kwargs: Any) -> int:
        return queryset.update(**kwargs)

    def delete(self, instance: T) -> None:
        instance.delete()

    def delete_by_id(self, pk: int) -> int:
        count, _ = self.get_queryset().filter(pk=pk).delete()
        return count

    def exists(self, **kwargs: Any) -> bool:
        return self.get_queryset().filter(**kwargs).exists()

    def count(self, **kwargs: Any) -> int:
        qs = self.get_queryset()
        if kwargs:
            qs = qs.filter(**kwargs)
        return qs.count()

    def first(self, **kwargs: Any) -> Optional[T]:
        return self.get_queryset().filter(**kwargs).first()

    def last(self, **kwargs: Any) -> Optional[T]:
        return self.get_queryset().filter(**kwargs).last()

    def get_or_create(self, defaults: Optional[dict] = None, **kwargs: Any) -> tuple[T, bool]:
        return self.model.objects.get_or_create(defaults=defaults, **kwargs)

    def update_or_create(self, defaults: Optional[dict] = None, **kwargs: Any) -> tuple[T, bool]:
        return self.model.objects.update_or_create(defaults=defaults, **kwargs)


class SoftDeleteRepository(BaseRepository[T]):

    def get_queryset(self) -> QuerySet[T]:
        return self.model.objects.filter(deleted_at__isnull=True)

    def get_with_deleted(self) -> QuerySet[T]:
        return self.model.objects.all()

    def get_only_deleted(self) -> QuerySet[T]:
        return self.model.objects.filter(deleted_at__isnull=False)

    def soft_delete(self, instance: T) -> T:
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at"])
        return instance

    def soft_delete_by_id(self, pk: int) -> int:
        return self.model.objects.filter(
            pk=pk, deleted_at__isnull=True
        ).update(deleted_at=timezone.now())

    def bulk_soft_delete(self, queryset: QuerySet[T]) -> int:
        return queryset.filter(deleted_at__isnull=True).update(
            deleted_at=timezone.now()
        )

    def restore(self, instance: T) -> T:
        instance.deleted_at = None
        instance.save(update_fields=["deleted_at"])
        return instance

    def restore_by_id(self, pk: int) -> int:
        return self.model.objects.filter(
            pk=pk, deleted_at__isnull=False
        ).update(deleted_at=None)

    def bulk_restore(self, queryset: QuerySet[T]) -> int:
        return queryset.filter(deleted_at__isnull=False).update(deleted_at=None)

    def hard_delete(self, instance: T) -> None:
        instance.delete()

    def hard_delete_by_id(self, pk: int) -> int:
        count, _ = self.model.objects.filter(pk=pk).delete()
        return count
