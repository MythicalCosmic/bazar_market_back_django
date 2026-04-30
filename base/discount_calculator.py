from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from base.models import Discount


def get_active_discounts():
    """Load all currently active discounts with their product/category mappings."""
    now = timezone.now()
    return (
        Discount.objects.filter(
            is_active=True,
            deleted_at__isnull=True,
        )
        .filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        )
        .prefetch_related("products", "categories")
    )


def build_discount_map(discounts=None):
    """
    Build lookup maps for efficient bulk discount resolution.

    Returns:
        (by_product, by_category) where each is {id: [discount_info, ...]}
    """
    if discounts is None:
        discounts = get_active_discounts()

    by_product = {}
    by_category = {}

    for d in discounts:
        info = {
            "id": d.id,
            "name_uz": d.name_uz,
            "type": d.type,
            "value": d.value,
            "max_discount": d.max_discount,
        }
        for p in d.products.all():
            by_product.setdefault(p.id, []).append(info)
        for c in d.categories.all():
            by_category.setdefault(c.id, []).append(info)

    return by_product, by_category


def calc_discount_amount(price, discount_type, value, max_discount=None):
    """Calculate the discount amount for a single discount rule."""
    if discount_type == "percent":
        amount = price * value / Decimal("100")
        if max_discount is not None:
            amount = min(amount, max_discount)
    else:
        amount = min(value, price)
    return amount


def apply_best_discount(price, product_id, category_id, by_product=None, by_category=None):
    """
    Find the best applicable discount and return the result.

    Args:
        price: Product price (Decimal)
        product_id: Product ID
        category_id: Category ID
        by_product: Discount map from build_discount_map()
        by_category: Discount map from build_discount_map()

    Returns:
        dict with discount_price, discount_amount, discount info — or None
    """
    if by_product is None or by_category is None:
        by_product, by_category = build_discount_map()

    candidates = []
    seen = set()

    for d in by_product.get(product_id, []):
        if d["id"] not in seen:
            seen.add(d["id"])
            candidates.append(d)

    for d in by_category.get(category_id, []):
        if d["id"] not in seen:
            seen.add(d["id"])
            candidates.append(d)

    if not candidates:
        return None

    best = None
    best_amount = Decimal("0")

    for d in candidates:
        amount = calc_discount_amount(price, d["type"], d["value"], d["max_discount"])
        if amount > best_amount:
            best_amount = amount
            best = d

    if best is None or best_amount <= 0:
        return None

    return {
        "discount_id": best["id"],
        "discount_name": best["name_uz"],
        "discount_type": best["type"],
        "discount_value": str(best["value"]),
        "discount_amount": str(best_amount),
        "discounted_price": str(price - best_amount),
    }


def apply_discount_to_product(product, by_product=None, by_category=None):
    """
    Attach discount info to a product instance.
    Sets product._discount_info (dict or None).
    """
    result = apply_best_discount(
        product.price, product.id, product.category_id,
        by_product, by_category,
    )
    product._discount_info = result
    return result


def apply_discounts_bulk(products, by_product=None, by_category=None):
    """
    Attach discount info to a list of products efficiently.
    Builds the discount map once and applies to all products.
    """
    if by_product is None or by_category is None:
        by_product, by_category = build_discount_map()

    for product in products:
        apply_discount_to_product(product, by_product, by_category)
