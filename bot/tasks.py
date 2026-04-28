import asyncio
import logging
from decimal import Decimal

from celery import shared_task

logger = logging.getLogger(__name__)


def _make_bot():
    from django.conf import settings
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def _run_async(coro_fn):
    """Run an async function that receives a fresh bot. Closes session after."""
    async def _wrapper():
        bot = _make_bot()
        try:
            await coro_fn(bot)
        finally:
            await bot.session.close()
    asyncio.run(_wrapper())


# ── Order status notification ──────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def task_notify_customer_status(self, order_id):
    try:
        from base.models import Order
        from bot.texts import status_label

        order = Order.objects.select_related("user").filter(pk=order_id).first()
        if not order:
            return

        user = order.user
        tg_id = user.telegram_id
        if not tg_id:
            return

        lang = user.language or "uz"

        STATUS_EMOJI = {
            "confirmed": "✅", "preparing": "👨‍🍳", "delivering": "🚗",
            "delivered": "📬", "completed": "✅", "cancelled": "❌",
        }
        STATUS_MSG = {
            "confirmed": {"uz": "Buyurtmangiz tasdiqlandi! Tayyorlanmoqda.", "ru": "Ваш заказ подтверждён! Готовится."},
            "preparing": {"uz": "Buyurtmangiz tayyorlanmoqda.", "ru": "Ваш заказ готовится."},
            "delivering": {"uz": "Buyurtmangiz yo'lda! Kuryer yetkazmoqda.", "ru": "Ваш заказ в пути! Курьер доставляет."},
            "delivered": {"uz": "Buyurtmangiz yetkazildi!", "ru": "Ваш заказ доставлен!"},
            "completed": {"uz": "Buyurtmangiz yakunlandi. Rahmat!", "ru": "Ваш заказ завершён. Спасибо!"},
            "cancelled": {"uz": "Buyurtmangiz bekor qilindi.", "ru": "Ваш заказ отменён."},
        }

        emoji = STATUS_EMOJI.get(order.status, "📋")
        status_text = status_label(order.status, lang)
        msg = STATUS_MSG.get(order.status, {}).get(lang, "")
        lbl_status = "Holat yangilandi" if lang != "ru" else "Статус обновлён"

        lines = [
            f"📦 <b>#{order.order_number}</b>",
            "",
            f"{emoji} {lbl_status}: <b>{status_text}</b>",
        ]
        if msg:
            lines.append(f"\n{msg}")
        if order.status == "cancelled" and order.cancel_reason:
            lbl_reason = "Sabab" if lang != "ru" else "Причина"
            lines.append(f"\n📝 {lbl_reason}: {order.cancel_reason}")

        text = "\n".join(lines)

        async def _send(bot):
            await bot.send_message(tg_id, text)

        _run_async(_send)

    except Exception as exc:
        if "chat not found" in str(exc).lower() or "bot was blocked" in str(exc).lower():
            logger.info(f"Customer {tg_id} unreachable (not started bot), skipping")
            return
        logger.exception(f"task_notify_customer_status failed for order {order_id}")
        raise self.retry(exc=exc)


# ── New order → admins ─────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def task_notify_admins_new_order(self, order_id):
    try:
        from base.models import Order, User
        from bot.keyboards import accept_print_keyboard
        from bot.texts import TEXTS

        order = Order.objects.select_related("user").prefetch_related("items").filter(pk=order_id).first()
        if not order:
            return

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
        item_lines = []
        for item in items:
            qty = f"{item.quantity:g}"
            item_lines.append(f"  • {item.product_name} — {qty} {item.unit} x {item.unit_price:,.0f} = {item.total:,.0f}")

        text = TEXTS["new_order"].format(
            order_number=order.order_number,
            customer=f"{order.user.first_name} {order.user.last_name}".strip(),
            phone=order.user.phone or "—",
            address=order.delivery_address_text or "—",
            total=f"{order.total:,.0f}",
            payment=order.get_payment_method_display() if order.payment_method else "—",
            items="\n".join(item_lines),
        )

        keyboard = accept_print_keyboard(order.id)

        async def _send(bot):
            for tg_id in admin_tg_ids:
                try:
                    await bot.send_message(tg_id, text, reply_markup=keyboard)
                except Exception as e:
                    logger.warning(f"Failed to notify admin {tg_id}: {e}")

        _run_async(_send)

    except Exception as exc:
        logger.warning(f"task_notify_admins_new_order failed: {exc}")
        raise self.retry(exc=exc)


# ── Banner broadcast ───────────────────────────────────────────

@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def task_broadcast_banner(self, banner_id):
    try:
        from base.models import Banner, User

        banner = Banner.objects.filter(pk=banner_id).first()
        if not banner:
            return

        tg_ids = list(
            User.objects.filter(
                role="client",
                telegram_id__isnull=False,
                is_active=True,
                deleted_at__isnull=True,
            ).values_list("telegram_id", flat=True)
        )
        if not tg_ids:
            return

        title = banner.title or ""
        caption = f"📰 <b>{title}</b>" if title else None
        image = banner.image or ""

        async def _send(bot):
            for tg_id in tg_ids:
                try:
                    if image:
                        await bot.send_photo(tg_id, photo=image, caption=caption)
                    elif caption:
                        await bot.send_message(tg_id, caption)
                except Exception as e:
                    logger.warning(f"Failed to send banner to {tg_id}: {e}")

        _run_async(_send)

    except Exception as exc:
        logger.warning(f"task_broadcast_banner failed: {exc}")
        raise self.retry(exc=exc)


# ── Cart price change ──────────────────────────────────────────

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def task_notify_cart_price_change(self, product_id, old_price_str, new_price_str):
    try:
        from base.models import CartItem, Product

        product = Product.objects.filter(pk=product_id).first()
        if not product:
            logger.info(f"cart_price_change: product {product_id} not found")
            return

        old_price = Decimal(old_price_str)
        new_price = Decimal(new_price_str)
        direction = "📉" if new_price < old_price else "📈"

        cart_users = list(
            CartItem.objects.filter(product_id=product_id)
            .select_related("user")
        )
        logger.info(f"cart_price_change: product={product_id}, cart_users={len(cart_users)}, old={old_price}, new={new_price}")
        if not cart_users:
            return

        async def _send(bot):
            for ci in cart_users:
                tg_id = ci.user.telegram_id
                logger.info(f"cart_price_change: user={ci.user.id}, tg_id={tg_id}")
                if not tg_id:
                    continue
                lang = ci.user.language or "uz"
                is_uz = lang != "ru"
                header = "Narx o'zgardi!" if is_uz else "Цена изменилась!"
                lbl_old = "Eski narx" if is_uz else "Старая цена"
                lbl_new = "Yangi narx" if is_uz else "Новая цена"
                footer = "Savatchangizda bu mahsulot bor." if is_uz else "Этот товар в вашей корзине."
                text = (
                    f"{direction} <b>{header}</b>\n\n"
                    f"<b>{product.name_uz}</b>\n"
                    f"{lbl_old}: {old_price:,.0f} UZS\n"
                    f"{lbl_new}: <b>{new_price:,.0f} UZS</b>\n\n"
                    f"<i>{footer}</i>"
                )
                try:
                    await bot.send_message(tg_id, text)
                except Exception as e:
                    logger.warning(f"Failed to notify cart user {tg_id}: {e}")

        _run_async(_send)

    except Exception as exc:
        logger.warning(f"task_notify_cart_price_change failed: {exc}")
        raise self.retry(exc=exc)


# ── Referral reward ────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def task_notify_referral_reward(self, user_id, coupon_code):
    try:
        from base.models import User

        user = User.objects.filter(pk=user_id).first()
        if not user or not user.telegram_id:
            return

        lang = user.language or "uz"
        is_uz = lang != "ru"

        header = "Tabriklaymiz!" if is_uz else "Поздравляем!"
        body = "Do'stingiz birinchi buyurtmasini berdi!" if is_uz else "Ваш друг сделал первый заказ!"
        lbl_coupon = "Sizning kupon kodingiz" if is_uz else "Ваш купон"
        footer = "Keyingi buyurtmangizda foydalaning!" if is_uz else "Используйте при следующем заказе!"

        text = (
            f"🎉 <b>{header}</b>\n\n"
            f"{body}\n\n"
            f"🎁 {lbl_coupon}:\n"
            f"   <code>{coupon_code}</code>\n\n"
            f"<i>{footer}</i>"
        )

        async def _send(bot):
            await bot.send_message(user.telegram_id, text)

        _run_async(_send)

    except Exception as exc:
        logger.warning(f"task_notify_referral_reward failed: {exc}")
        raise self.retry(exc=exc)


# ── Cart abandonment reminder (periodic) ──────────────────────

@shared_task
def task_cart_abandonment_reminders():
    from django.core.cache import cache
    from django.utils import timezone
    from datetime import timedelta
    from base.models import CartItem, User
    from base.repositories.setting import SettingRepository

    setting_repo = SettingRepository()
    hours = int(setting_repo.get_value("cart_reminder_hours", "24"))
    cutoff = timezone.now() - timedelta(hours=hours)

    user_ids = list(
        CartItem.objects.filter(added_at__lte=cutoff)
        .values_list("user_id", flat=True)
        .distinct()
    )

    if not user_ids:
        return

    users = list(
        User.objects.filter(
            pk__in=user_ids,
            telegram_id__isnull=False,
            is_active=True,
            deleted_at__isnull=True,
        )
    )

    if not users:
        return

    async def _send(bot):
        for user in users:
            cache_key = f"cart_reminder:{user.id}"
            if cache.get(cache_key):
                continue

            lang = user.language or "uz"
            is_uz = lang != "ru"
            text = (
                f"🛒 <b>{'Savatchangizda mahsulotlar kutmoqda!' if is_uz else 'В вашей корзине ждут товары!'}</b>\n\n"
                f"<i>{'Buyurtma berishni unutmang!' if is_uz else 'Не забудьте оформить заказ!'}</i>"
            )

            try:
                await bot.send_message(user.telegram_id, text)
                cache.set(cache_key, True, hours * 3600)
            except Exception as e:
                logger.warning(f"Failed to send cart reminder to {user.telegram_id}: {e}")

    _run_async(_send)
