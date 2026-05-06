import asyncio
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Telegram bot (long polling)."

    def handle(self, *args, **options):
        from bot.bot_instance import dp, get_bot
        from bot.handlers import start, admin
        from bot.middleware import DjangoUserMiddleware

        dp.update.middleware(DjangoUserMiddleware())
        dp.include_router(start.router)
        dp.include_router(admin.router)

        async def _run():
            bot = get_bot()
            # Drop any stale webhook so getUpdates doesn't conflict.
            await bot.delete_webhook(drop_pending_updates=True)
            try:
                await dp.start_polling(bot)
            finally:
                await bot.session.close()

        self.stdout.write(self.style.SUCCESS("Starting Telegram bot..."))
        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Bot stopped by user"))
