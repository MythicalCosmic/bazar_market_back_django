import asyncio
import logging
from decimal import Decimal
from html import escape as h

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
    async def _wrapper():
        bot = _make_bot()
        try:
            await coro_fn(bot)
        finally:
            await bot.session.close()
    asyncio.run(_wrapper())


def _is_recipient_unreachable(exc) -> bool:
    """Block / kicked / chat-not-found errors are not retryable."""
    from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
    if isinstance(exc, TelegramForbiddenError):
        return True
    if isinstance(exc, TelegramBadRequest):
        msg = str(exc).lower()
        return "chat not found" in msg or "user is deactivated" in msg
    return False


async def _send_with_retry(bot, send_kwargs, send_method="send_message"):
    """Send with TelegramRetryAfter handling. Returns True on success, False if recipient unreachable, raises otherwise."""
    from aiogram.exceptions import TelegramRetryAfter
    method = getattr(bot, send_method)
    while True:
        try:
            await method(**send_kwargs)
            return True
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception as exc:
            if _is_recipient_unreachable(exc):
                return False
            raise


# ── Order status notification ──────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def task_notify_customer_status(self, order_id):
    from base.models import Order
    from bot.texts import status_label

    order = Order.objects.select_related("user").filter(pk=order_id).first()
    if not order or not order.user.telegram_id:
        return

    user = order.user
    tg_id = user.telegram_id
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
        lines.append(f"\n📝 {lbl_reason}: {h(order.cancel_reason)}")

    text = "\n".join(lines)

    async def _send(bot):
        delivered = await _send_with_retry(bot, {"chat_id": tg_id, "text": text})
        if not delivered:
            logger.info("Customer %s unreachable; skipping", tg_id)

    try:
        _run_async(_send)
    except Exception as exc:
        logger.exception("task_notify_customer_status failed for order %s", order_id)
        raise self.retry(exc=exc)


# ── New order → admins ─────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def task_notify_admins_new_order(self, order_id):
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
        item_lines.append(f"  • {h(item.product_name)} — {qty} {h(item.unit)} x {item.unit_price:,.0f} = {item.total:,.0f}")

    text = TEXTS["new_order"].format(
        order_number=order.order_number,
        customer=h(f"{order.user.first_name} {order.user.last_name}".strip()),
        phone=h(order.user.phone or "—"),
        address=h(order.delivery_address_text or "—"),
        total=f"{order.total:,.0f}",
        payment=order.get_payment_method_display() if order.payment_method else "—",
        items="\n".join(item_lines),
    )

    keyboard = accept_print_keyboard(order.id)

    async def _send(bot):
        for tg_id in admin_tg_ids:
            try:
                delivered = await _send_with_retry(
                    bot, {"chat_id": tg_id, "text": text, "reply_markup": keyboard}
                )
                if not delivered:
                    logger.info("Admin %s unreachable; skipping", tg_id)
            except Exception as exc:
                # Per-recipient infra failure — log and move on, don't fail the broadcast.
                logger.warning("Failed to notify admin %s: %s", tg_id, exc)

    try:
        _run_async(_send)
    except Exception as exc:
        logger.exception("task_notify_admins_new_order failed: %s", exc)
        raise self.retry(exc=exc)


# ── Banner broadcast ───────────────────────────────────────────

@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def task_broadcast_banner(self, banner_id):
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
    caption = f"📰 <b>{h(title)}</b>" if title else None
    image = banner.image or ""

    async def _send(bot):
        for tg_id in tg_ids:
            try:
                if image:
                    await _send_with_retry(
                        bot, {"chat_id": tg_id, "photo": image, "caption": caption},
                        send_method="send_photo",
                    )
                elif caption:
                    await _send_with_retry(bot, {"chat_id": tg_id, "text": caption})
            except Exception as exc:
                logger.warning("Failed to send banner to %s: %s", tg_id, exc)

    try:
        _run_async(_send)
    except Exception as exc:
        logger.warning("task_broadcast_banner failed: %s", exc)
        raise self.retry(exc=exc)


# ── Cart price change ──────────────────────────────────────────

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def task_notify_cart_price_change(self, product_id, old_price_str, new_price_str):
    from base.models import CartItem, Product

    product = Product.objects.filter(pk=product_id).first()
    if not product:
        return

    old_price = Decimal(old_price_str)
    new_price = Decimal(new_price_str)
    direction = "📉" if new_price < old_price else "📈"

    cart_users = list(
        CartItem.objects.filter(
            product_id=product_id,
            user__is_active=True,
            user__deleted_at__isnull=True,
            user__telegram_id__isnull=False,
        ).select_related("user")
    )
    if not cart_users:
        return

    async def _send(bot):
        for ci in cart_users:
            tg_id = ci.user.telegram_id
            lang = ci.user.language or "uz"
            is_uz = lang != "ru"
            header = "Narx o'zgardi!" if is_uz else "Цена изменилась!"
            lbl_old = "Eski narx" if is_uz else "Старая цена"
            lbl_new = "Yangi narx" if is_uz else "Новая цена"
            footer = "Savatchangizda bu mahsulot bor." if is_uz else "Этот товар в вашей корзине."
            text = (
                f"{direction} <b>{header}</b>\n\n"
                f"<b>{h(product.name_uz)}</b>\n"
                f"{lbl_old}: {old_price:,.0f} UZS\n"
                f"{lbl_new}: <b>{new_price:,.0f} UZS</b>\n\n"
                f"<i>{footer}</i>"
            )
            try:
                await _send_with_retry(bot, {"chat_id": tg_id, "text": text})
            except Exception as exc:
                logger.warning("Failed to notify cart user %s: %s", tg_id, exc)

    try:
        _run_async(_send)
    except Exception as exc:
        logger.warning("task_notify_cart_price_change failed: %s", exc)
        raise self.retry(exc=exc)


# ── Referral reward ────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def task_notify_referral_reward(self, user_id, coupon_code):
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
        f"   <code>{h(coupon_code)}</code>\n\n"
        f"<i>{footer}</i>"
    )

    async def _send(bot):
        await _send_with_retry(bot, {"chat_id": user.telegram_id, "text": text})

    try:
        _run_async(_send)
    except Exception as exc:
        logger.warning("task_notify_referral_reward failed: %s", exc)
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

    ttl = max(hours * 3600, 3600)

    async def _send(bot):
        for user in users:
            cache_key = f"cart_reminder:{user.id}"
            # Atomic claim — if another worker already sent, skip.
            if not cache.add(cache_key, 1, ttl):
                continue

            lang = user.language or "uz"
            is_uz = lang != "ru"
            text = (
                f"🛒 <b>{'Savatchangizda mahsulotlar kutmoqda!' if is_uz else 'В вашей корзине ждут товары!'}</b>\n\n"
                f"<i>{'Buyurtma berishni unutmang!' if is_uz else 'Не забудьте оформить заказ!'}</i>"
            )

            try:
                delivered = await _send_with_retry(bot, {"chat_id": user.telegram_id, "text": text})
                if not delivered:
                    # Recipient unreachable — release the slot so we can try again next cycle if their state changes.
                    cache.delete(cache_key)
            except Exception as exc:
                cache.delete(cache_key)
                logger.warning("Failed to send cart reminder to %s: %s", user.telegram_id, exc)

    _run_async(_send)


# ── Periodic session cleanup ───────────────────────────────────

@shared_task
def task_cleanup_expired_sessions():
    from base.repositories.session import SessionRepository
    count = SessionRepository().clear_expired()
    if count:
        logger.info("Cleared %d expired sessions", count)
    return {"cleared": count}
