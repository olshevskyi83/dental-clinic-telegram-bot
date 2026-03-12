from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Записатися на прийом")],
            [KeyboardButton(text="Мої записи")],
            [KeyboardButton(text="Відмінити запис")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Оберіть дію",
    )


def admin_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Адмін-панель")],
            [KeyboardButton(text="Записатися на прийом")],
            [KeyboardButton(text="Мої записи")],
            [KeyboardButton(text="Відмінити запис")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Оберіть дію",
    )