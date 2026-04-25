from aiogram.fsm.state import State, StatesGroup


class LanguageSelection(StatesGroup):
    choosing = State()


class MainMenu(StatesGroup):
    active = State()
