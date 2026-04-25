from base.interfaces.review import IReviewRepository
from base.interfaces.order import IOrderRepository
from base.exceptions import NotFoundError, ValidationError
from customer.dto.review import CreateReviewDTO


class CustomerReviewService:
    def __init__(
        self,
        review_repository: IReviewRepository,
        order_repository: IOrderRepository,
    ):
        self.review_repo = review_repository
        self.order_repo = order_repository

    def submit_review(self, user_id: int, dto: CreateReviewDTO) -> dict:
        order = self.order_repo.get_by_id(dto.order_id)
        if not order or order.user_id != user_id:
            raise NotFoundError("Order not found")

        if order.status not in ("delivered", "completed"):
            raise ValidationError("You can only review delivered orders")

        if self.review_repo.has_reviewed(user_id, dto.order_id):
            raise ValidationError("You have already reviewed this order")

        if not (1 <= dto.rating <= 5):
            raise ValidationError("Rating must be between 1 and 5")

        review = self.review_repo.create(
            user_id=user_id,
            order_id=dto.order_id,
            rating=dto.rating,
            comment=dto.comment.strip(),
            moderation_status="pending",
        )
        return {"id": review.id, "message": "Review submitted"}

    def list_my_reviews(self, user_id: int, page=1, per_page=20):
        qs = self.review_repo.get_by_user(user_id).select_related("order")
        return self.review_repo.paginate(qs, page, per_page)
