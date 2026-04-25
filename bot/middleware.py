from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from asgiref.sync import sync_to_async


class DjangoUserMiddleware(BaseMiddleware):
    """Resolve Django User from telegram_id for every update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user:
            from base.models import User
            data["django_user"] = await sync_to_async(
                User.objects.filter(
                    telegram_id=tg_user.id,
                    deleted_at__isnull=True,
                ).first
            )()
            if data["django_user"]:
                data["lang"] = data["django_user"].language
            else:
                data["lang"] = "uz"
        else:
            data["django_user"] = None
            data["lang"] = "uz"

        return await handler(event, data)
