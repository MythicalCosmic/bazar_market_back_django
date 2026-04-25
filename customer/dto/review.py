from dataclasses import dataclass


@dataclass(frozen=True)
class CreateReviewDTO:
    order_id: int
    rating: int
    comment: str = ""
