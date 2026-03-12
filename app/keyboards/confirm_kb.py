from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_booking_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Підтвердити запис",
                    callback_data="confirm_booking"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="cancel_booking"
                )
            ],
        ]
    )