from decimal import Decimal, InvalidOperation

from base.interfaces.cart import ICartItemRepository
from base.interfaces.product import IProductRepository
from base.exceptions import NotFoundError, ValidationError
from base.discount_calculator import build_discount_map, apply_best_discount


class CartService:
    def __init__(
        self,
        cart_repository: ICartItemRepository,
        product_repository: IProductRepository,
    ):
        self.cart_repo = cart_repository
        self.product_repo = product_repository

    def get_cart(self, user_id: int) -> dict:
        items = list(self.cart_repo.get_by_user(user_id))
        subtotal = Decimal(0)
        cart_items = []

        by_product, by_category = build_discount_map() if items else ({}, {})

        for item in items:
            p = item.product
            if not p or p.deleted_at or not p.is_active:
                continue

            disc_info = apply_best_discount(p.price, p.id, p.category_id, by_product, by_category)
            unit_price = Decimal(disc_info["discounted_price"]) if disc_info else p.price
            line_total = unit_price * item.quantity
            subtotal += line_total
            cart_items.append({
                "product_id": p.id,
                "name_uz": p.name_uz,
                "name_ru": p.name_ru,
                "price": str(p.price),
                "discounted_price": str(unit_price) if disc_info else None,
                "unit": p.unit,
                "quantity": str(item.quantity),
                "line_total": str(line_total),
                "in_stock": p.in_stock,
                "stock_qty": str(p.stock_qty) if p.stock_qty is not None else None,
            })

        return {
            "items": cart_items,
            "item_count": len(cart_items),
            "subtotal": str(subtotal),
        }

    def add_item(self, user_id: int, product_id: int, quantity_str: str) -> dict:
        product = self.product_repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise NotFoundError("Product not found or unavailable")

        if not product.in_stock:
            raise ValidationError("Product is out of stock")

        quantity = self._validate_quantity(product, quantity_str)

        self.cart_repo.add_item(user_id, product_id, quantity)
        return {"message": "Item added to cart", "product_id": product_id, "quantity": str(quantity)}

    def update_quantity(self, user_id: int, product_id: int, quantity_str: str) -> dict:
        try:
            quantity = Decimal(quantity_str)
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid quantity")

        if quantity <= 0:
            self.cart_repo.remove_item(user_id, product_id)
            return {"message": "Item removed from cart"}

        product = self.product_repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise NotFoundError("Product not found or unavailable")

        quantity = self._validate_quantity(product, quantity_str)

        item = self.cart_repo.get_by_user_and_product(user_id, product_id)
        if not item:
            raise NotFoundError("Item not in cart")

        self.cart_repo.update_quantity(item, quantity)
        return {"message": "Cart updated", "product_id": product_id, "quantity": str(quantity)}

    def remove_item(self, user_id: int, product_id: int) -> dict:
        removed = self.cart_repo.remove_item(user_id, product_id)
        if not removed:
            raise NotFoundError("Item not in cart")
        return {"message": "Item removed from cart"}

    def clear_cart(self, user_id: int) -> dict:
        count = self.cart_repo.clear_cart(user_id)
        return {"message": f"Cart cleared ({count} items removed)"}

    def cart_count(self, user_id: int) -> int:
        return self.cart_repo.cart_count(user_id)

    @staticmethod
    def _validate_quantity(product, quantity_str: str) -> Decimal:
        try:
            quantity = Decimal(quantity_str)
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid quantity")

        if quantity <= 0:
            raise ValidationError("Quantity must be positive")

        if product.min_qty and quantity < product.min_qty:
            raise ValidationError(f"Minimum quantity is {product.min_qty}")

        if product.max_qty and quantity > product.max_qty:
            raise ValidationError(f"Maximum quantity is {product.max_qty}")

        if product.step:
            remainder = quantity % product.step
            if remainder != 0:
                raise ValidationError(f"Quantity must be in steps of {product.step}")

        if product.stock_qty is not None and quantity > product.stock_qty:
            raise ValidationError(f"Only {product.stock_qty} available in stock")

        return quantity
