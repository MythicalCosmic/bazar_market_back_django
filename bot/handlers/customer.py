from aiogram import Router, F
from aiogram.types import Message
from asgiref.sync import sync_to_async

from bot.states import MainMenu
from bot.texts import t, TEXTS, status_label, status_emoji, payment_label
from bot.utils import aget_bot_username

router = Router()


def _match_button(key: str):
    """Match message text against both UZ and RU button labels."""
    vals = TEXTS.get(key, {})
    if isinstance(vals, dict):
        return F.text.in_({vals.get("uz", ""), vals.get("ru", "")})
    return F.text == vals


def _product_name(product, lang: str) -> str:
    if lang == "ru" and product.name_ru:
        return product.name_ru
    return product.name_uz


def _cat_name(category, lang: str) -> str:
    if not category:
        return ""
    if lang == "ru" and category.name_ru:
        return category.name_ru
    return category.name_uz


def _discount_name(d, lang: str) -> str:
    if lang == "ru" and d.name_ru:
        return d.name_ru
    return d.name_uz


# ── Orders ─────────────────────────────────────────────────────

@router.message(MainMenu.active, _match_button("my_orders"))
async def my_orders(message: Message, django_user, lang: str, **kwargs):
    if not django_user:
        await message.answer(t("no_orders", lang))
        return

    from base.models import Order
    orders = await sync_to_async(list)(
        Order.objects.filter(user_id=django_user.id)
        .select_related("address")
        .prefetch_related("items")
        .order_by("-created_at")[:5]
    )

    if not orders:
        await message.answer(t("no_orders", lang))
        return

    is_uz = lang != "ru"
    lbl_status = "Holat" if is_uz else "Статус"
    lbl_date = "Sana" if is_uz else "Дата"
    lbl_address = "Manzil" if is_uz else "Адрес"
    lbl_products = "Mahsulotlar" if is_uz else "Товары"
    lbl_subtotal = "Jami" if is_uz else "Итого"
    lbl_delivery = "Yetkazish" if is_uz else "Доставка"
    lbl_discount = "Chegirma" if is_uz else "Скидка"
    lbl_total = "Umumiy" if is_uz else "Всего"
    lbl_payment = "To'lov" if is_uz else "Оплата"
    lbl_note = "Izoh" if is_uz else "Заметка"

    for o in orders:
        emoji = status_emoji(o.status)
        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            f"📦 <b>#{o.order_number}</b>",
            "",
            f"{emoji} {lbl_status}: <b>{status_label(o.status, lang)}</b>",
            f"📅 {lbl_date}: {o.created_at.strftime('%d.%m.%Y %H:%M')}",
        ]

        addr = o.delivery_address_text
        if addr:
            lines.append(f"📍 {lbl_address}: {addr}")

        items = list(o.items.all())
        if items:
            lines.append(f"\n🛒 <b>{lbl_products}:</b>")
            for item in items:
                qty = f"{item.quantity:g}"
                lines.append(
                    f"  • {item.product_name} — {qty} {item.unit} "
                    f"x {item.unit_price:,.0f} = {item.total:,.0f}"
                )

        lines.append("")
        lines.append(f"💰 {lbl_subtotal}: {o.subtotal:,.0f} UZS")
        if o.delivery_fee:
            lines.append(f"🚚 {lbl_delivery}: {o.delivery_fee:,.0f} UZS")
        if o.discount:
            lines.append(f"🏷 {lbl_discount}: -{o.discount:,.0f} UZS")
        lines.append(f"💵 <b>{lbl_total}: {o.total:,.0f} UZS</b>")

        if o.payment_method:
            lines.append(f"\n💳 {lbl_payment}: {payment_label(o.payment_method, lang)}")
        if o.user_note:
            lines.append(f"📝 {lbl_note}: {o.user_note}")

        lines.append("━━━━━━━━━━━━━━━━━━━━")

        await message.answer("\n".join(lines))


# ── Favorites ──────────────────────────────────────────────────

@router.message(MainMenu.active, _match_button("favorites"))
async def my_favorites(message: Message, django_user, lang: str, **kwargs):
    if not django_user:
        await message.answer(t("no_favorites", lang))
        return

    from base.models import Favorite
    favs = await sync_to_async(list)(
        Favorite.objects.filter(user_id=django_user.id)
        .select_related("product", "product__category")
        .order_by("-created_at")[:10]
    )

    if not favs:
        await message.answer(t("no_favorites", lang))
        return

    header = "❤️  <b>Sevimli mahsulotlar</b>" if lang != "ru" else "❤️  <b>Избранные товары</b>"
    lines = [header, ""]

    for i, f in enumerate(favs, 1):
        p = f.product
        name = _product_name(p, lang)
        cat = _cat_name(p.category, lang)
        cat_suffix = f" · {cat}" if cat else ""
        lines.append(f"<b>{i}.</b> {name}")
        lines.append(f"   💰 {p.price:,.0f} UZS{cat_suffix}")
        lines.append("")

    await message.answer("\n".join(lines))


# ── Referral ───────────────────────────────────────────────────

@router.message(MainMenu.active, _match_button("referral"))
async def my_referral(message: Message, django_user, lang: str, **kwargs):
    if not django_user:
        await message.answer(t("referral_not_registered", lang))
        return

    from base.models import Referral
    from django.db.models import Sum

    code = str(django_user.uuid)[:8].upper()
    count = await sync_to_async(Referral.objects.filter(referrer_id=django_user.id).count)()
    rewards_agg = await sync_to_async(
        Referral.objects.filter(referrer_id=django_user.id, is_rewarded=True).aggregate
    )(total=Sum("reward_amount"))
    rewards = rewards_agg.get("total") or 0

    bot_username = await aget_bot_username()
    await message.answer(t("referral_info", lang).format(
        code=code,
        link=f"https://t.me/{bot_username}?start=ref_{code}",
        count=count,
        rewards=f"{rewards:,.0f}",
    ))


# ── Discounts ──────────────────────────────────────────────────

@router.message(MainMenu.active, _match_button("discounts"))
async def active_discounts(message: Message, lang: str, **kwargs):
    from base.models import Discount
    from django.db.models import Q
    from django.utils import timezone

    now = timezone.now()
    discounts = await sync_to_async(list)(
        Discount.objects.filter(
            is_active=True, deleted_at__isnull=True,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        ).order_by("-created_at")[:10]
    )

    if not discounts:
        await message.answer(t("no_discounts", lang))
        return

    is_uz = lang != "ru"
    header = "🏷  <b>Faol chegirmalar</b>" if is_uz else "🏷  <b>Активные скидки</b>"
    lbl_until = "gacha" if is_uz else "до"
    lbl_no_expiry = "Muddatsiz" if is_uz else "Бессрочно"

    lines = [header, ""]

    for d in discounts:
        name = _discount_name(d, lang)
        if d.type == "percent":
            val = f"{d.value:g}%"
            if d.max_discount:
                val += f" · max {d.max_discount:,.0f} UZS"
        else:
            val = f"{d.value:,.0f} UZS"

        if d.expires_at:
            expiry = f"⏰ {d.expires_at.strftime('%d.%m.%Y')} {lbl_until}"
        else:
            expiry = f"⏰ {lbl_no_expiry}"

        lines.append(f"┌ <b>{name}</b>")
        lines.append(f"│ 📉 {val}")
        lines.append(f"│ {expiry}")
        lines.append("└───────────────")
        lines.append("")

    await message.answer("\n".join(lines))


# ── News / Banners ─────────────────────────────────────────────

@router.message(MainMenu.active, _match_button("news"))
async def news_banners(message: Message, lang: str, **kwargs):
    from base.models import Banner
    from django.db.models import Q
    from django.utils import timezone

    now = timezone.now()
    banners = await sync_to_async(list)(
        Banner.objects.filter(
            is_active=True,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        ).order_by("sort_order")[:5]
    )

    if not banners:
        no_news = {"uz": "Hozircha yangiliklar yo'q.", "ru": "Новостей пока нет."}
        await message.answer(no_news.get(lang, no_news["uz"]))
        return

    for b in banners:
        title = b.title or ""
        caption = f"📰 <b>{title}</b>" if title else None

        if b.image:
            try:
                await message.answer_photo(photo=b.image, caption=caption)
                continue
            except Exception:
                pass

        if caption:
            await message.answer(caption)
