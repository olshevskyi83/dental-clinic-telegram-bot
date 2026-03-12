from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def my_appointments_keyboard(appointments):
    keyboard = []

    for item in appointments:
        keyboard.append([
            InlineKeyboardButton(
                text=f"#{item['id']} | {item['slot_date']} {item['slot_time']} | {item['status']}",
                callback_data=f"my_appointment_view:{item['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="❌ Закрити",
            callback_data="my_appointments_close"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def my_appointment_actions_keyboard(appointment_id: int, status: str, calendar_url: str | None = None):
    rows = []

    if status == "confirmed" and calendar_url:
        rows.append([
            InlineKeyboardButton(
                text="📅 Додати в Google Calendar",
                url=calendar_url
            )
        ])

    if status in ("pending", "confirmed"):
        rows.append([
            InlineKeyboardButton(
                text="❌ Відмінити запис",
                callback_data=f"my_appointment_cancel:{appointment_id}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            text="⬅ Назад до списку",
            callback_data="my_appointments_list"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_appointments_keyboard(appointments):
    keyboard = []

    for item in appointments:
        keyboard.append([
            InlineKeyboardButton(
                text=f"#{item['id']} | {item['slot_date']} {item['slot_time']} | {item['status']}",
                callback_data=f"cancel_pick:{item['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="❌ Закрити",
            callback_data="cancel_close"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def cancel_confirm_keyboard(appointment_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Так, відмінити",
                    callback_data=f"cancel_confirm:{appointment_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅ Назад",
                    callback_data="cancel_back_to_list"
                )
            ],
        ]
    )


def patient_confirmed_notification_keyboard(calendar_url: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Додати в Google Calendar",
                    url=calendar_url
                )
            ]
        ]
    )