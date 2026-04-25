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


def main_menu_keyboard(lang: str, is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = []

    webapp_url = getattr(settings, "WEBAPP_URL", "")
    if webapp_url:
        buttons.append([KeyboardButton(
            text=t("open_webapp", lang),
            web_app=WebAppInfo(url=webapp_url),
        )])

    buttons.append([
        KeyboardButton(text=t("my_orders", lang)),
        KeyboardButton(text=t("favorites", lang)),
    ])
    buttons.append([
        KeyboardButton(text=t("referral", lang)),
        KeyboardButton(text=t("discounts", lang)),
    ])
    buttons.append([
        KeyboardButton(text=t("news", lang)),
    ])

    if is_admin:
        buttons.append([KeyboardButton(text=t("admin_panel", lang))])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def admin_panel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("admin_stats", lang), callback_data="admin_stats")],
    ])


def accept_print_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Qabul qilish va chop etish / Принять и печатать",
            callback_data=f"accept_print:{order_id}",
        )],
    ])
