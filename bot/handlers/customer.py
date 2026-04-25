from aiogram import Router, F
from aiogram.types import Message
from asgiref.sync import sync_to_async

from bot.states import MainMenu
from bot.texts import t, TEXTS

router = Router()


def _match_button(key: str):
    """Match message text against both UZ and RU button labels."""
    vals = TEXTS.get(key, {})
    if isinstance(vals, dict):
        return F.text.in_({vals.get("uz", ""), vals.get("ru", "")})
    return F.text == vals


@router.message(MainMenu.active, _match_button("my_orders"))
async def my_orders(message: Message, django_user, lang: str, **kwargs):
    if not django_user:
        await message.answer(t("no_orders", lang))
        return

    from base.models import Order
    orders = await sync_to_async(list)(
        Order.objects.filter(user_id=django_user.id)
        .order_by("-created_at")[:10]
        .values("order_number", "status", "total", "created_at")
    )

    if not orders:
        await message.answer(t("no_orders", lang))
        return

    lines = []
    for o in orders:
        lines.append(
            f"📋 #{o['order_number']} — {o['status']}\n"
            f"   💰 {o['total']:,.0f} UZS | {o['created_at'].strftime('%d.%m.%Y')}"
        )
    await message.answer("\n\n".join(lines))


@router.message(MainMenu.active, _match_button("favorites"))
async def my_favorites(message: Message, django_user, lang: str, **kwargs):
    if not django_user:
        await message.answer(t("no_favorites", lang))
        return

    from base.models import Favorite
    favs = await sync_to_async(list)(
        Favorite.objects.filter(user_id=django_user.id)
        .select_related("product")
        .order_by("-created_at")[:10]
    )

    if not favs:
        await message.answer(t("no_favorites", lang))
        return

    lines = []
    for f in favs:
        p = f.product
        lines.append(f"❤️ {p.name_uz} — {p.price:,.0f} UZS")
    await message.answer("\n".join(lines))


@router.message(MainMenu.active, _match_button("referral"))
async def my_referral(message: Message, django_user, lang: str, **kwargs):
    if not django_user:
        await message.answer(t("referral_info", lang).format(code="—", link="—", count=0, rewards=0))
        return

    from base.models import Referral
    from django.db.models import Sum

    code = str(django_user.uuid)[:8].upper()
    count = await sync_to_async(Referral.objects.filter(referrer_id=django_user.id).count)()
    rewards_agg = await sync_to_async(
        Referral.objects.filter(referrer_id=django_user.id, is_rewarded=True).aggregate
    )(total=Sum("reward_amount"))
    rewards = rewards_agg.get("total") or 0

    await message.answer(t("referral_info", lang).format(
        code=code,
        link=f"https://t.me/BazarMarketBot?start=ref_{code}",
        count=count,
        rewards=f"{rewards:,.0f}",
    ))


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

    lines = []
    for d in discounts:
        val = f"{d.value}%" if d.type == "percent" else f"{d.value:,.0f} UZS"
        lines.append(f"🏷 {d.name_uz} — {val}")
    await message.answer("\n".join(lines))


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
        text = f"📰 <b>{b.title}</b>" if b.title else "📰"
        await message.answer(text)
