from django.db.models import Avg, Count, Q
from django.utils import timezone

from base.interfaces.review import IReviewRepository
from base.interfaces.user import IUserRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.review import UpdateReviewDTO


class ReviewService:
    def __init__(
        self,
        review_repository: IReviewRepository,
        user_repository: IUserRepository,
    ):
        self.review_repo = review_repository
        self.user_repo = user_repository

    def get_all(
        self,
        query=None,
        rating=None,
        moderation_status=None,
        user_id=None,
        order_by="-created_at",
        page=1,
        per_page=20,
    ):
        qs = self.review_repo.get_all().select_related("user", "order")

        if query:
            qs = self.review_repo.search(qs, query, ["comment", "user__first_name", "user__phone", "order__order_number"])
        if rating is not None:
            qs = qs.filter(rating=rating)
        if moderation_status:
            qs = qs.filter(moderation_status=moderation_status)
        if user_id is not None:
            qs = qs.filter(user_id=user_id)

        qs = self.review_repo.apply_ordering(
            qs, order_by, {"created_at", "rating", "moderation_status"}
        )
        return self.review_repo.paginate(qs, page, per_page)

    def get_by_id(self, review_id: int):
        return (
            self.review_repo.get_all()
            .select_related("user", "order", "moderated_by")
            .filter(pk=review_id)
            .first()
        )

    def approve(self, review_id: int, admin_user) -> dict:
        review = self.review_repo.get_by_id(review_id)
        if not review:
            raise NotFoundError("Review not found")
        self.review_repo.update(
            review,
            moderation_status="approved",
            moderated_by=admin_user,
            moderated_at=timezone.now(),
        )
        return {"message": "Review approved"}

    def reject(self, review_id: int, admin_user) -> dict:
        review = self.review_repo.get_by_id(review_id)
        if not review:
            raise NotFoundError("Review not found")
        self.review_repo.update(
            review,
            moderation_status="rejected",
            moderated_by=admin_user,
            moderated_at=timezone.now(),
        )
        return {"message": "Review rejected"}

    def reply(self, review_id: int, reply_text: str, admin_user) -> dict:
        review = self.review_repo.get_by_id(review_id)
        if not review:
            raise NotFoundError("Review not found")
        if not reply_text.strip():
            raise ValidationError("Reply text cannot be empty")
        self.review_repo.update(review, admin_reply=reply_text.strip())
        return {"message": "Reply added"}

    def delete_review(self, review_id: int) -> dict:
        review = self.review_repo.get_by_id(review_id)
        if not review:
            raise NotFoundError("Review not found")
        self.review_repo.delete(review)
        return {"message": "Review deleted"}

    def bulk_approve(self, review_ids: list[int], admin_user) -> dict:
        qs = self.review_repo.get_all().filter(pk__in=review_ids, moderation_status="pending")
        count = qs.update(
            moderation_status="approved",
            moderated_by=admin_user,
            moderated_at=timezone.now(),
        )
        return {"approved": count, "skipped": len(review_ids) - count}

    def bulk_reject(self, review_ids: list[int], admin_user) -> dict:
        qs = self.review_repo.get_all().filter(pk__in=review_ids, moderation_status="pending")
        count = qs.update(
            moderation_status="rejected",
            moderated_by=admin_user,
            moderated_at=timezone.now(),
        )
        return {"rejected": count, "skipped": len(review_ids) - count}

    def stats(self, date_from=None, date_to=None) -> dict:
        qs = self.review_repo.get_all()

        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        total = qs.count()
        avg_rating = qs.aggregate(avg=Avg("rating"))["avg"]
        by_rating = dict(
            qs.values_list("rating")
            .annotate(c=Count("id"))
            .values_list("rating", "c")
        )
        by_status = dict(
            qs.values_list("moderation_status")
            .annotate(c=Count("id"))
            .values_list("moderation_status", "c")
        )

        return {
            "total": total,
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "by_rating": {str(k): v for k, v in sorted(by_rating.items())},
            "by_moderation_status": by_status,
            "pending": by_status.get("pending", 0),
            "approved": by_status.get("approved", 0),
            "rejected": by_status.get("rejected", 0),
            "with_comment": qs.exclude(comment="").count(),
            "with_reply": qs.exclude(admin_reply="").count(),
        }
