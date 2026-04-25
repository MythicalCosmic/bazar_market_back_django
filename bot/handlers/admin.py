from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from asgiref.sync import sync_to_async

from bot.states import MainMenu
from bot.texts import t, TEXTS
from bot.keyboards import admin_panel_keyboard

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


@router.callback_query(F.data.startswith("accept_print:"))
async def accept_and_print(callback: CallbackQuery, django_user, lang: str, **kwargs):
    if not django_user or django_user.role not in ADMIN_ROLES:
        await callback.answer("Access denied", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])

    from base.container import container
    from admins.services.v1.order_service import OrderService
    from base.printing.print_queue import enqueue_print

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
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        await callback.answer(str(e)[:200], show_alert=True)
