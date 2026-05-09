from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from asgiref.sync import sync_to_async

from bot.states import LanguageSelection, MainMenu
from bot.texts import t
from bot.keyboards import language_keyboard, main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, django_user, lang: str, **kwargs):
    if not django_user:
        await state.set_state(LanguageSelection.choosing)
        await message.answer(
            t("choose_language"),
            reply_markup=language_keyboard(),
        )
        return

    lang = django_user.language or "uz"
    await state.set_state(MainMenu.active)
    await message.answer(
        t("welcome", lang),
        reply_markup=main_menu_keyboard(lang),
    )


@router.callback_query(LanguageSelection.choosing, F.data.in_({"lang_uz", "lang_ru"}))
async def language_chosen(callback: CallbackQuery, state: FSMContext, django_user, **kwargs):
    lang = "uz" if callback.data == "lang_uz" else "ru"

    if django_user:
        from base.models import User
        await sync_to_async(
            User.objects.filter(pk=django_user.id).update
        )(language=lang)

    await state.set_state(MainMenu.active)
    await callback.message.delete()
    await callback.message.answer(
        t("welcome", lang),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()


@router.message(LanguageSelection.choosing)
async def language_not_chosen(message: Message, **kwargs):
    await message.answer(t("choose_language"), reply_markup=language_keyboard())


@router.callback_query(LanguageSelection.choosing)
async def language_callback_invalid(callback: CallbackQuery, **kwargs):
    await callback.answer(t("choose_language"), show_alert=True)
