from dataclasses import dataclass


@dataclass(frozen=True)
class AddCartItemDTO:
    product_id: int
    quantity: str


@dataclass(frozen=True)
class UpdateCartItemDTO:
    product_id: int
    quantity: str
