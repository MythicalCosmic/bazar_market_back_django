from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    WebAppInfo,
)
from django.conf import settings
from bot.texts import t


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        ]
    ])


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    buttons = []

    webapp_url = getattr(settings, "WEBAPP_URL", "")
    if webapp_url:
        buttons.append([KeyboardButton(
            text=t("open_webapp", lang),
            web_app=WebAppInfo(url=webapp_url),
        )])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)




def order_actions_keyboard(order_id: int, status: str, payment_status: str) -> InlineKeyboardMarkup:
    """Build inline buttons for valid status transitions + payment status."""
    from bot.texts import STATUS_LABELS

    TRANSITIONS = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["preparing", "cancelled"],
        "preparing": ["delivering", "cancelled"],
        "delivering": ["delivered", "cancelled"],
        "delivered": ["completed"],
    }

    STATUS_EMOJI = {
        "confirmed": "✅", "preparing": "👨‍🍳", "delivering": "🚗",
        "delivered": "📬", "completed": "✅", "cancelled": "❌",
    }

    PAYMENT_LABELS = {
        "unpaid": "To'lanmagan", "pending": "Kutilmoqda",
        "paid": "To'langan", "refunded": "Qaytarilgan",
    }

    rows = []

    # Status transition buttons
    allowed = TRANSITIONS.get(status, [])
    if allowed:
        status_buttons = []
        for s in allowed:
            emoji = STATUS_EMOJI.get(s, "")
            label = STATUS_LABELS.get(s, {}).get("uz", s)
            status_buttons.append(
                InlineKeyboardButton(text=f"{emoji} {label}", callback_data=f"os:{order_id}:{s}")
            )
        rows.append(status_buttons)

    # Payment status buttons
    pay_buttons = []
    if payment_status != "paid":
        pay_buttons.append(
            InlineKeyboardButton(text="💰 To'langan", callback_data=f"op:{order_id}:paid")
        )
    if payment_status == "paid":
        pay_buttons.append(
            InlineKeyboardButton(text="↩️ Qaytarish", callback_data=f"op:{order_id}:refunded")
        )
    if pay_buttons:
        rows.append(pay_buttons)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def accept_print_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Qabul qilish va chop etish / Принять и печатать",
            callback_data=f"accept_print:{order_id}",
        )],
    ])
