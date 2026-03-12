from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import ADMIN_IDS
from app.keyboards.reply import admin_main_menu_keyboard, main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id in ADMIN_IDS:
        markup = admin_main_menu_keyboard()
    else:
        markup = main_menu_keyboard()

    await message.answer(
        "Вітаю! Це бот стоматологічної клініки.\n\n"
        "Тут можна записатися на прийом, переглянути свої записи або скасувати запис.",
        reply_markup=markup,
    )