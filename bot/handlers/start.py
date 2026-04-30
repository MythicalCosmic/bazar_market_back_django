from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from asgiref.sync import sync_to_async

from bot.states import LanguageSelection, MainMenu
from bot.texts import t
from bot.keyboards import language_keyboard, main_menu_keyboard

router = Router()


async def _try_apply_referral(message: Message, django_user, code: str, lang: str):
    try:
        from base.container import container
        from customer.services.v1.referral_service import CustomerReferralService
        svc = container.resolve(CustomerReferralService)
        await sync_to_async(svc.apply_referral)(django_user.id, code)
        await message.answer(t("referral_applied", lang))
    except Exception:
        pass


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, django_user, lang: str, **kwargs):
    # Parse referral deep link: /start ref_ABCD1234
    deep_link = message.text.split(maxsplit=1)[1] if " " in message.text else None
    referral_code = deep_link[4:] if deep_link and deep_link.startswith("ref_") else None

    # Auto-register new Telegram users
    is_new_user = False
    if not django_user:
        from base.models import User
        django_user = await sync_to_async(User.objects.create)(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name or "User",
            last_name=message.from_user.last_name or "",
            role=User.Role.CLIENT,
            language="uz",
        )
        is_new_user = True

    # User exists with language set — skip to main menu
    if django_user.language:
        lang = django_user.language
        await state.set_state(MainMenu.active)

        # Only apply referral for newly registered users
        if referral_code and is_new_user:
            await _try_apply_referral(message, django_user, referral_code, lang)

        await message.answer(
            t("welcome", lang),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    # No language set — store referral code in FSM, ask for language
    if referral_code and is_new_user:
        await state.update_data(referral_code=referral_code)

    await state.set_state(LanguageSelection.choosing)
    await message.answer(t("choose_language"), reply_markup=language_keyboard())


@router.callback_query(LanguageSelection.choosing, F.data.in_({"lang_uz", "lang_ru"}))
async def language_chosen(callback: CallbackQuery, state: FSMContext, django_user, **kwargs):
    lang = "uz" if callback.data == "lang_uz" else "ru"
    data = await state.get_data()
    await state.update_data(language=lang)

    # Re-fetch user if middleware cached None (user was just created in cmd_start)
    if not django_user and callback.from_user:
        from base.models import User
        django_user = await sync_to_async(
            User.objects.filter(telegram_id=callback.from_user.id, deleted_at__isnull=True).first
        )()

    # Save language to Django DB
    if django_user:
        from base.models import User
        await sync_to_async(
            User.objects.filter(pk=django_user.id).update
        )(language=lang)

    await state.set_state(MainMenu.active)

    # Apply referral if stored from deep link
    referral_code = data.get("referral_code")
    if referral_code and django_user:
        await _try_apply_referral(callback.message, django_user, referral_code, lang)

    await callback.message.delete()
    await callback.message.answer(
        t("welcome", lang),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()


# Hard lock: any other input during language selection re-asks
@router.message(LanguageSelection.choosing)
async def language_not_chosen(message: Message, **kwargs):
    await message.answer(t("choose_language"), reply_markup=language_keyboard())


@router.callback_query(LanguageSelection.choosing)
async def language_callback_invalid(callback: CallbackQuery, **kwargs):
    await callback.answer(t("choose_language"), show_alert=True)
