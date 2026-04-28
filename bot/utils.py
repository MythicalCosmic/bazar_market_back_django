from asgiref.sync import sync_to_async


def get_bot_username() -> str:
    from base.repositories.setting import SettingRepository
    return SettingRepository().get_value("bot_username", "BazarMarketBot")


async def aget_bot_username() -> str:
    return await sync_to_async(get_bot_username)()
