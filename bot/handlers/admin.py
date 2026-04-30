from aiogram import Router, F
from aiogram.types import CallbackQuery
from asgiref.sync import sync_to_async

from bot.texts import t
from bot.keyboards import order_actions_keyboard

router = Router()

ADMIN_ROLES = {"admin", "manager"}


@router.callback_query(F.data.startswith("os:"))
async def update_order_status(callback: CallbackQuery, django_user, lang: str, **kwargs):
    """Update order status. Callback: os:{order_id}:{new_status}"""
    if not django_user or django_user.role not in ADMIN_ROLES:
        await callback.answer("Access denied", show_alert=True)
        return

    parts = callback.data.split(":")
    order_id = int(parts[1])
    new_status = parts[2]

    from base.container import container
    from admins.services.v1.order_service import OrderService
    from bot.texts import status_label

    svc = container.resolve(OrderService)
    try:
        result = await sync_to_async(svc.update_status)(
            order_id, new_status, django_user, "Updated via Telegram"
        )

        # If confirmed, also print
        if new_status == "confirmed":
            from base.printing.print_queue import enqueue_print
            await sync_to_async(enqueue_print)(order_id)

        status_text = status_label(new_status, lang)
        order_number = result.get("order_id", order_id)
        await callback.answer(
            t("order_status_updated", lang).format(order_number=order_number, status=status_text),
            show_alert=True,
        )

        # Refresh the message with updated buttons
        from base.models import Order
        order = await sync_to_async(
            Order.objects.select_related("user").filter(pk=order_id).first
        )()
        if order:
            from bot.texts import status_emoji, payment_label
            emoji = status_emoji(order.status)
            user_name = f"{order.user.first_name} {order.user.last_name}".strip()
            text = (
                f"📦 <b>#{order.order_number}</b>\n"
                f"👤 {user_name} | {order.user.phone or '—'}\n"
                f"{emoji} {status_label(order.status, lang)}\n"
                f"💰 {order.total:,.0f} so'm | 💳 {payment_label(order.payment_method, lang)}\n"
                f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
            kb = order_actions_keyboard(order.id, order.status, order.payment_status)
            await callback.message.edit_text(text, reply_markup=kb if kb.inline_keyboard else None)

    except Exception as e:
        await callback.answer(str(e)[:200], show_alert=True)


@router.callback_query(F.data.startswith("op:"))
async def update_payment_status(callback: CallbackQuery, django_user, lang: str, **kwargs):
    """Update payment status. Callback: op:{order_id}:{new_payment_status}"""
    if not django_user or django_user.role not in ADMIN_ROLES:
        await callback.answer("Access denied", show_alert=True)
        return

    parts = callback.data.split(":")
    order_id = int(parts[1])
    new_payment = parts[2]

    from base.container import container
    from admins.services.v1.order_service import OrderService
    from bot.texts import status_label

    PAYMENT_LABELS = {
        "unpaid": "To'lanmagan", "pending": "Kutilmoqda",
        "paid": "To'langan", "refunded": "Qaytarilgan",
    }

    svc = container.resolve(OrderService)
    try:
        result = await sync_to_async(svc.update_payment_status)(
            order_id, new_payment, django_user
        )

        pay_text = PAYMENT_LABELS.get(new_payment, new_payment)
        await callback.answer(
            t("order_payment_updated", lang).format(order_number=order_id, status=pay_text),
            show_alert=True,
        )

        # Refresh the message with updated buttons
        from base.models import Order
        from bot.texts import status_emoji, payment_label
        order = await sync_to_async(
            Order.objects.select_related("user").filter(pk=order_id).first
        )()
        if order:
            emoji = status_emoji(order.status)
            user_name = f"{order.user.first_name} {order.user.last_name}".strip()
            text = (
                f"📦 <b>#{order.order_number}</b>\n"
                f"👤 {user_name} | {order.user.phone or '—'}\n"
                f"{emoji} {status_label(order.status, lang)}\n"
                f"💰 {order.total:,.0f} so'm | 💳 {payment_label(order.payment_method, lang)}\n"
                f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
            kb = order_actions_keyboard(order.id, order.status, order.payment_status)
            await callback.message.edit_text(text, reply_markup=kb if kb.inline_keyboard else None)

    except Exception as e:
        await callback.answer(str(e)[:200], show_alert=True)



@router.callback_query(F.data.startswith("accept_print:"))
async def accept_and_print(callback: CallbackQuery, django_user, lang: str, **kwargs):
    if not django_user or django_user.role not in ADMIN_ROLES:
        await callback.answer("Access denied", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])

    from base.container import container
    from admins.services.v1.order_service import OrderService
    from base.printing.print_queue import enqueue_print
    from base.models import Order

    svc = container.resolve(OrderService)
    try:
        result = await sync_to_async(svc.update_status)(
            order_id, "confirmed", django_user, "Accepted via Telegram"
        )
        await sync_to_async(enqueue_print)(order_id)

        order_number = result.get("order_id", order_id)
        await callback.answer(
            t("order_accepted", lang).format(order_number=order_number),
            show_alert=True,
        )

        # Replace "Accept & Print" with order management buttons
        order = await sync_to_async(
            Order.objects.select_related("user").filter(pk=order_id).first
        )()
        if order:
            from bot.texts import status_label, status_emoji, payment_label
            emoji = status_emoji(order.status)
            user_name = f"{order.user.first_name} {order.user.last_name}".strip()
            text = (
                f"📦 <b>#{order.order_number}</b>\n"
                f"👤 {user_name} | {order.user.phone or '—'}\n"
                f"{emoji} {status_label(order.status, lang)}\n"
                f"💰 {order.total:,.0f} so'm | 💳 {payment_label(order.payment_method, lang)}\n"
                f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
            kb = order_actions_keyboard(order.id, order.status, order.payment_status)
            await callback.message.edit_text(text, reply_markup=kb)
        else:
            await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        await callback.answer(str(e)[:200], show_alert=True)
