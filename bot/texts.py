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
        "uz": (
            "┌─────────────────────┐\n"
            "   🎁  REFERAL DASTURI\n"
            "└─────────────────────┘\n\n"
            "📋 Sizning kodingiz:\n"
            "   <code>{code}</code>\n\n"
            "🔗 Havola:\n"
            "   {link}\n\n"
            "👥 Taklif qilganlar: <b>{count}</b> ta\n"
            "💰 Mukofotlar: <b>{rewards} UZS</b>\n\n"
            "<i>Do'stlaringizni taklif qiling va\n"
            "har bir buyurtma uchun mukofot oling!</i>"
        ),
        "ru": (
            "┌─────────────────────┐\n"
            "   🎁  РЕФЕРАЛЬНАЯ ПРОГРАММА\n"
            "└─────────────────────┘\n\n"
            "📋 Ваш код:\n"
            "   <code>{code}</code>\n\n"
            "🔗 Ссылка:\n"
            "   {link}\n\n"
            "👥 Приглашённые: <b>{count}</b>\n"
            "💰 Награды: <b>{rewards} UZS</b>\n\n"
            "<i>Приглашайте друзей и получайте\n"
            "награды за каждый заказ!</i>"
        ),
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
    "referral_applied": {
        "uz": "🎁 Referal kod muvaffaqiyatli qo'llanildi!",
        "ru": "🎁 Реферальный код успешно применён!",
    },
    "referral_not_registered": {
        "uz": "🎁 Referal kodingizni olish uchun avval ro'yxatdan o'ting.",
        "ru": "🎁 Зарегистрируйтесь, чтобы получить реферальный код.",
    },
    "admin_banners": {
        "uz": "🖼 Bannerlar",
        "ru": "🖼 Баннеры",
    },
    "no_banners": {
        "uz": "Hozircha faol bannerlar yo'q.",
        "ru": "Активных баннеров пока нет.",
    },
}


STATUS_LABELS = {
    "pending":    {"uz": "Kutilmoqda",     "ru": "Ожидает"},
    "confirmed":  {"uz": "Tasdiqlangan",   "ru": "Подтверждён"},
    "preparing":  {"uz": "Tayyorlanmoqda", "ru": "Готовится"},
    "delivering": {"uz": "Yetkazilmoqda",  "ru": "Доставляется"},
    "delivered":  {"uz": "Yetkazildi",     "ru": "Доставлен"},
    "completed":  {"uz": "Yakunlandi",     "ru": "Завершён"},
    "cancelled":  {"uz": "Bekor qilindi",  "ru": "Отменён"},
}

STATUS_EMOJI = {
    "pending": "⏳", "confirmed": "✅", "preparing": "👨‍🍳",
    "delivering": "🚗", "delivered": "📬", "completed": "✅", "cancelled": "❌",
}

PAYMENT_LABELS = {
    "cash": {"uz": "Naqd", "ru": "Наличные"},
    "card": {"uz": "Karta", "ru": "Карта"},
}


def t(key: str, lang: str = "uz") -> str:
    val = TEXTS.get(key)
    if val is None:
        return key
    if isinstance(val, dict):
        return val.get(lang, val.get("uz", key))
    return val


def status_label(status: str, lang: str = "uz") -> str:
    return STATUS_LABELS.get(status, {}).get(lang, status)


def status_emoji(status: str) -> str:
    return STATUS_EMOJI.get(status, "📋")


def payment_label(method: str, lang: str = "uz") -> str:
    return PAYMENT_LABELS.get(method, {}).get(lang, method or "—")
