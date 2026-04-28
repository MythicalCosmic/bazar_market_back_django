import base64
import logging
import os
from decimal import Decimal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from base.printing.consumers import PRINTER_GROUP

logger = logging.getLogger(__name__)

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "base_images", "image.png")
_logo_cache = None


def _get_logo_base64() -> str:
    global _logo_cache
    if _logo_cache is not None:
        return _logo_cache
    if os.path.isfile(_LOGO_PATH):
        with open(_LOGO_PATH, "rb") as f:
            _logo_cache = base64.b64encode(f.read()).decode("ascii")
    else:
        _logo_cache = ""
    return _logo_cache


def enqueue_print(order_id: int):
    """Send a print job to all connected printer agents via WebSocket."""
    try:
        receipt_data = _build_receipt_data(order_id)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            PRINTER_GROUP,
            {
                "type": "print_job",
                "data": receipt_data,
            },
        )
        logger.info(f"Print job sent for order {order_id}")
    except Exception as e:
        logger.error(f"Failed to send print job for order {order_id}: {e}")


def _build_receipt_data(order_id: int) -> dict:
    """Build structured receipt data from an Order."""
    from base.models import Order

    order = (
        Order.objects
        .select_related("user")
        .prefetch_related("items")
        .get(pk=order_id)
    )

    user = order.user
    items = []
    for item in order.items.all():
        items.append({
            "name": item.product_name,
            "qty": str(item.quantity),
            "unit": item.unit,
            "unit_price": str(item.unit_price),
            "total": str(item.total),
        })

    pay_labels = {"cash": "Naqd", "card": "Karta"}
    pay_status = {
        "unpaid": "TO'LANMAGAN", "pending": "KUTILMOQDA",
        "paid": "TO'LANGAN", "refunded": "QAYTARILGAN",
    }

    return {
        "logo": _get_logo_base64(),
        "order_id": order.id,
        "order_number": order.order_number,
        "customer_name": f"{user.first_name} {user.last_name}".strip() or "—",
        "customer_phone": user.phone or "",
        "address": order.delivery_address_text or "",
        "payment_method": pay_labels.get(order.payment_method, order.payment_method or ""),
        "payment_status": pay_status.get(order.payment_status, order.payment_status.upper()),
        "items": items,
        "subtotal": str(order.subtotal),
        "delivery_fee": str(order.delivery_fee),
        "discount": str(order.discount),
        "total": str(order.total),
        "user_note": order.user_note or "",
    }
