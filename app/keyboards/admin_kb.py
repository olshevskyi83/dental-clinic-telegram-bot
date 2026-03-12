from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def admin_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Адмін-панель")],
            [KeyboardButton(text="Записатися на прийом")],
            [KeyboardButton(text="Мої записи")],
            [KeyboardButton(text="Відмінити запис")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Оберіть дію"
    )


def admin_panel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗂 Керування слотами",
                    callback_data="admin_slots_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Всі записи",
                    callback_data="admin_list_appointments"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Записи на сьогодні",
                    callback_data="admin_list_today_appointments"
                )
            ],
        ]
    )


def admin_slots_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Додати слот",
                    callback_data="admin_add_slot"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Доступні слоти",
                    callback_data="admin_list_available_slots"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗂 Всі слоти",
                    callback_data="admin_list_all_slots"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅ Назад",
                    callback_data="admin_back_to_panel"
                )
            ],
        ]
    )


def admin_slot_actions_keyboard(slot_id: int, slot_status: str):
    rows = []

    if slot_status == "available":
        rows.append([
            InlineKeyboardButton(
                text="🔒 Заблокувати",
                callback_data=f"admin_block_slot:{slot_id}"
            )
        ])
    elif slot_status == "blocked":
        rows.append([
            InlineKeyboardButton(
                text="🔓 Розблокувати",
                callback_data=f"admin_unblock_slot:{slot_id}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            text="🗑 Видалити слот",
            callback_data=f"admin_delete_slot:{slot_id}"
        )
    ])
    rows.append([
        InlineKeyboardButton(
            text="⬅ Назад до слотів",
            callback_data="admin_list_all_slots"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def appointments_list_keyboard(appointments):
    keyboard = []

    for item in appointments:
        keyboard.append([
            InlineKeyboardButton(
                text=f"#{item['id']} | {item['slot_date']} {item['slot_time']} | {item['full_name']} | {item['status']}",
                callback_data=f"admin_appointment_view:{item['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅ Назад",
            callback_data="admin_back_to_panel"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def appointment_actions_keyboard(appointment_id: int, status: str, calendar_url: str | None = None):
    rows = []

    if calendar_url and status in ("confirmed", "pending"):
        rows.append([
            InlineKeyboardButton(
                text="📅 Додати в Google Calendar",
                url=calendar_url
            )
        ])

    if status != "confirmed":
        rows.append([
            InlineKeyboardButton(
                text="✅ Підтвердити",
                callback_data=f"admin_confirm_appointment:{appointment_id}"
            )
        ])

    if status != "completed":
        rows.append([
            InlineKeyboardButton(
                text="✔ Завершено",
                callback_data=f"admin_complete_appointment:{appointment_id}"
            )
        ])

    if status != "cancelled":
        rows.append([
            InlineKeyboardButton(
                text="❌ Скасувати",
                callback_data=f"admin_cancel_appointment:{appointment_id}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            text="🗑 Видалити запис",
            callback_data=f"admin_delete_appointment:{appointment_id}"
        )
    ])

    rows.append([
        InlineKeyboardButton(
            text="⬅ Назад до записів",
            callback_data="admin_list_appointments"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)