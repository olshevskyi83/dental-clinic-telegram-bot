from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def available_dates_keyboard(dates):
    keyboard = []

    for row in dates:
        slot_date = row["slot_date"]
        keyboard.append([
            InlineKeyboardButton(
                text=slot_date,
                callback_data=f"slot_date:{slot_date}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="❌ Скасувати",
            callback_data="cancel_booking"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def available_times_keyboard(slots, selected_date: str):
    keyboard = []

    for row in slots:
        slot_id = row["id"]
        slot_time = row["slot_time"]

        keyboard.append([
            InlineKeyboardButton(
                text=slot_time,
                callback_data=f"slot_pick:{slot_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅ Назад до дат",
            callback_data="back_to_dates"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="❌ Скасувати",
            callback_data="cancel_booking"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)