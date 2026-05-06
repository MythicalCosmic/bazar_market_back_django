from django.conf import settings
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

_bot = None


def _make_storage():
    redis_url = getattr(settings, "REDIS_URL", None) or "redis://localhost:6379/0"
    try:
        from aiogram.fsm.storage.redis import RedisStorage
        return RedisStorage.from_url(redis_url)
    except Exception:
        from aiogram.fsm.storage.memory import MemoryStorage
        return MemoryStorage()


dp = Dispatcher(storage=_make_storage())


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _bot
