from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from asgiref.sync import sync_to_async

from bot.states import MainMenu
from bot.texts import t, TEXTS
from bot.keyboards import admin_panel_keyboard, order_actions_keyboard

router = Router()

ADMIN_ROLES = {"admin", "manager"}


def _match_button(key: str):
    vals = TEXTS.get(key, {})
    if isinstance(vals, dict):
        return F.text.in_({vals.get("uz", ""), vals.get("ru", "")})
    return F.text == vals


@router.message(MainMenu.active, _match_button("admin_panel"))
async def admin_panel(message: Message, django_user, lang: str, **kwargs):
    if not django_user or django_user.role not in ADMIN_ROLES:
        return

    await message.answer(t("admin_panel", lang), reply_markup=admin_panel_keyboard(lang))


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, django_user, lang: str, **kwargs):
    if not django_user or django_user.role not in ADMIN_ROLES:
        await callback.answer("Access denied", show_alert=True)
        return

    from base.models import Order, Product, User
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    orders_today = await sync_to_async(Order.objects.filter(created_at__gte=today).count)()
    pending = await sync_to_async(Order.objects.filter(status="pending").count)()

    revenue_today = await sync_to_async(
        lambda: Order.objects.filter(
            created_at__gte=today
        ).exclude(status="cancelled").aggregate(s=Sum("total"))["s"] or 0
    )()

    total_products = await sync_to_async(
        Product.objects.filter(is_active=True, deleted_at__isnull=True).count
    )()
    total_customers = await sync_to_async(
        User.objects.filter(role="client", is_active=True, deleted_at__isnull=True).count
    )()

    text = (
        f"📊 <b>Statistika / Статистика</b>\n\n"
        f"📦 Bugun buyurtmalar: {orders_today}\n"
        f"⏳ Kutilmoqda: {pending}\n"
        f"💰 Bugungi tushum: {revenue_today:,.0f} UZS\n"
        f"🛒 Mahsulotlar: {total_products}\n"
        f"👥 Mijozlar: {total_customers}"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery, django_user, lang: str, **kwargs):
    if not django_user or django_user.role not in ADMIN_ROLES:
        await callback.answer("Access denied", show_alert=True)
        return

    from base.models import Order
    from bot.texts import status_label, status_emoji, payment_label

    orders = await sync_to_async(list)(
        Order.objects.select_related("user")
        .exclude(status__in=["completed", "cancelled"])
        .order_by("-created_at")[:10]
    )

    if not orders:
        await callback.message.answer(t("no_active_orders", lang))
        await callback.answer()
        return

    for o in orders:
        emoji = status_emoji(o.status)
        user_name = f"{o.user.first_name} {o.user.last_name}".strip()
        text = (
            f"📦 <b>#{o.order_number}</b>\n"
            f"👤 {user_name} | {o.user.phone or '—'}\n"
            f"{emoji} {status_label(o.status, lang)}\n"
            f"💰 {o.total:,.0f} so'm | 💳 {payment_label(o.payment_method, lang)}\n"
            f"📅 {o.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
        kb = order_actions_keyboard(o.id, o.status, o.payment_status)
        await callback.message.answer(text, reply_markup=kb)

    await callback.answer()


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


@router.callback_query(F.data == "admin_banners")
async def admin_banners(callback: CallbackQuery, django_user, lang: str, **kwargs):
    if not django_user or django_user.role not in ADMIN_ROLES:
        await callback.answer("Access denied", show_alert=True)
        return

    from base.models import Banner
    from django.db.models import Q
    from django.utils import timezone

    now = timezone.now()
    banners = await sync_to_async(list)(
        Banner.objects.filter(is_active=True)
        .filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        )
        .order_by("sort_order")[:20]
    )

    if not banners:
        await callback.message.answer(t("no_banners", lang))
        await callback.answer()
        return

    lines = []
    for b in banners:
        title = b.title or f"Banner #{b.id}"
        lines.append(f"🖼 <b>{title}</b> (#{b.id}, sort: {b.sort_order})")
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "admin_back_to_panel")
async def back_to_panel(callback: CallbackQuery, django_user, lang: str, **kwargs):
    if not django_user or django_user.role not in ADMIN_ROLES:
        await callback.answer("Access denied", show_alert=True)
        return

    await callback.message.edit_text(t("admin_panel", lang), reply_markup=admin_panel_keyboard(lang))
    await callback.answer()


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
