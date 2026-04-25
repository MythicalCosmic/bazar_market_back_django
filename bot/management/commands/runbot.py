import asyncio

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the Telegram bot"

    def handle(self, *args, **options):
        from bot.bot_instance import dp, get_bot
        from bot.handlers import start, customer, admin
        from bot.middleware import DjangoUserMiddleware

        dp.update.middleware(DjangoUserMiddleware())
        dp.include_router(start.router)
        dp.include_router(customer.router)
        dp.include_router(admin.router)

        self.stdout.write(self.style.SUCCESS("Starting Telegram bot..."))
        asyncio.run(dp.start_polling(get_bot()))
