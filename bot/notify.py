import asyncio
import logging

logger = logging.getLogger(__name__)


def notify_admins_new_order(order):
    """Send Telegram notification to all admin users about a new order.
    Called from Django (sync context) after order placement."""
    from base.models import User

    admin_tg_ids = list(
        User.objects.filter(
            role__in=["admin", "manager"],
            telegram_id__isnull=False,
            is_active=True,
            deleted_at__isnull=True,
        ).values_list("telegram_id", flat=True)
    )

    if not admin_tg_ids:
        return

    items = list(order.items.all())
    text = _format_order(order, items)

    from bot.keyboards import accept_print_keyboard
    keyboard = accept_print_keyboard(order.id)

    async def _send():
        from bot.bot_instance import get_bot
        b = get_bot()
        for tg_id in admin_tg_ids:
            try:
                await b.send_message(tg_id, text, reply_markup=keyboard)
            except Exception as e:
                logger.warning(f"Failed to notify admin {tg_id}: {e}")

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send())
    except RuntimeError:
        asyncio.run(_send())


def _format_order(order, items) -> str:
    item_lines = []
    for item in items:
        qty = f"{item.quantity:g}"
        item_lines.append(f"  • {item.product_name} — {qty} {item.unit} x {item.unit_price:,.0f} = {item.total:,.0f}")

    from bot.texts import TEXTS
    return TEXTS["new_order"].format(
        order_number=order.order_number,
        customer=f"{order.user.first_name} {order.user.last_name}".strip(),
        phone=order.user.phone or "—",
        address=order.delivery_address_text or "—",
        total=f"{order.total:,.0f}",
        payment=order.get_payment_method_display() if order.payment_method else "—",
        items="\n".join(item_lines),
    )
