TEXTS = {
    "choose_language": "🌐 Tilni tanlang / Выберите язык",
    "welcome": {
        "uz": "Bazar Market-ga xush kelibsiz! 🛒",
        "ru": "Добро пожаловать в Bazar Market! 🛒",
    },
    "main_menu": {
        "uz": "Asosiy menyu:",
        "ru": "Главное меню:",
    },
    "open_webapp": {
        "uz": "🛍 Do'konni ochish",
        "ru": "🛍 Открыть магазин",
    },
    "my_orders": {
        "uz": "📦 Buyurtmalarim",
        "ru": "📦 Мои заказы",
    },
    "favorites": {
        "uz": "❤️ Sevimlilar",
        "ru": "❤️ Избранное",
    },
    "referral": {
        "uz": "🎁 Referal",
        "ru": "🎁 Реферал",
    },
    "discounts": {
        "uz": "🏷 Chegirmalar",
        "ru": "🏷 Скидки",
    },
    "news": {
        "uz": "📰 Yangiliklar",
        "ru": "📰 Новости",
    },
    "no_orders": {
        "uz": "Sizda hali buyurtmalar yo'q.",
        "ru": "У вас пока нет заказов.",
    },
    "no_favorites": {
        "uz": "Sizda hali sevimlilar yo'q.",
        "ru": "У вас пока нет избранного.",
    },
    "no_discounts": {
        "uz": "Hozircha faol chegirmalar yo'q.",
        "ru": "Сейчас нет активных скидок.",
    },
    "referral_info": {
        "uz": "🎁 Sizning referal kodingiz: <code>{code}</code>\n\nHavola: {link}\n\nJalb qilinganlar: {count}\nMukofotlar: {rewards} UZS",
        "ru": "🎁 Ваш реферальный код: <code>{code}</code>\n\nСсылка: {link}\n\nПриглашённые: {count}\nНаграды: {rewards} UZS",
    },
    "admin_panel": {
        "uz": "⚙️ Admin panel",
        "ru": "⚙️ Админ панель",
    },
    "admin_stats": {
        "uz": "📊 Statistika",
        "ru": "📊 Статистика",
    },
    "new_order": "🆕 <b>Yangi buyurtma / Новый заказ</b>\n\n"
                 "📋 #{order_number}\n"
                 "👤 {customer}\n"
                 "📱 {phone}\n"
                 "📍 {address}\n"
                 "💰 {total} UZS\n"
                 "💳 {payment}\n\n"
                 "{items}",
    "order_accepted": {
        "uz": "✅ Buyurtma #{order_number} qabul qilindi va chop etilmoqda!",
        "ru": "✅ Заказ #{order_number} принят и отправлен на печать!",
    },
}


def t(key: str, lang: str = "uz") -> str:
    val = TEXTS.get(key)
    if val is None:
        return key
    if isinstance(val, dict):
        return val.get(lang, val.get("uz", key))
    return val
