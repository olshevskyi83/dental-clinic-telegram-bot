from datetime import datetime
import sqlite3

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.filters.admin import IsAdminFilter
from app.keyboards.admin_kb import (
    admin_menu_keyboard,
    admin_panel_keyboard,
    admin_slot_actions_keyboard,
    admin_slots_menu_keyboard,
    appointment_actions_keyboard,
    appointments_list_keyboard,
)
from app.keyboards.appointments_kb import patient_confirmed_notification_keyboard
from app.keyboards.reply import main_menu_keyboard
from app.services.booking_service import (
    admin_block_slot,
    admin_create_slot,
    admin_delete_booking,
    admin_delete_slot,
    admin_get_all_slots,
    admin_get_available_slots,
    admin_unblock_slot,
    admin_update_booking_status,
    build_google_calendar_url,
    get_booking_details,
    get_bookings_list,
    get_slot_details,
    get_todays_bookings,
)
from app.states.admin import AdminSlotStates

router = Router()
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


def is_valid_date(date_text: str) -> bool:
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_valid_time(time_text: str) -> bool:
    try:
        datetime.strptime(time_text, "%H:%M")
        return True
    except ValueError:
        return False


def _all_slots_keyboard(slots):
    keyboard = []

    for slot in slots:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{slot['id']} | {slot['slot_date']} {slot['slot_time']} | {slot['status']}",
                callback_data=f"admin_slot_view:{slot['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅ Назад",
            callback_data="admin_slots_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def format_appointment_details(booking) -> str:
    notes_text = booking["notes"] if booking["notes"] else "Не вказано"
    phone_text = booking["phone"] if booking["phone"] else "Не вказано"
    age_text = booking["age"] if booking["age"] is not None else "Не вказано"

    return (
        f"Запис #{booking['id']}\n\n"
        f"Клієнт: {booking['client_code']}\n"
        f"Пацієнт: {booking['full_name']}\n"
        f"Телефон: {phone_text}\n"
        f"Вік: {age_text}\n"
        f"Дата: {booking['slot_date']}\n"
        f"Час: {booking['slot_time']}\n"
        f"Статус запису: {booking['status']}\n"
        f"Статус слота: {booking['slot_status']}\n"
        f"Коментар: {notes_text}\n"
        f"Створено: {booking['created_at']}"
    )


@router.message(lambda message: message.text == "Адмін-панель")
async def admin_panel(message: Message):
    await message.answer(
        "Адмін-панель",
        reply_markup=admin_panel_keyboard(),
    )


@router.callback_query(lambda c: c.data == "admin_back_to_panel")
async def admin_back_to_panel(callback: CallbackQuery):
    await callback.message.edit_text(
        "Адмін-панель",
        reply_markup=admin_panel_keyboard(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_slots_menu")
async def admin_slots_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Керування слотами",
        reply_markup=admin_slots_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_add_slot")
async def admin_add_slot_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AdminSlotStates.waiting_for_slot_date)

    await callback.message.edit_text(
        "Введіть дату нового слота у форматі YYYY-MM-DD\n"
        "Наприклад: 2026-03-20"
    )
    await callback.answer()


@router.message(AdminSlotStates.waiting_for_slot_date)
async def admin_process_slot_date(message: Message, state: FSMContext):
    slot_date = (message.text or "").strip()

    if not is_valid_date(slot_date):
        await message.answer("Некоректна дата. Приклад: 2026-03-20")
        return

    await state.update_data(slot_date=slot_date)
    await state.set_state(AdminSlotStates.waiting_for_slot_time)

    await message.answer(
        "Введіть час нового слота у форматі HH:MM\n"
        "Наприклад: 10:30"
    )


@router.message(AdminSlotStates.waiting_for_slot_time)
async def admin_process_slot_time(message: Message, state: FSMContext):
    slot_time = (message.text or "").strip()

    if not is_valid_time(slot_time):
        await message.answer("Некоректний час. Приклад: 10:30")
        return

    data = await state.get_data()
    slot_date = data["slot_date"]

    try:
        slot_id = admin_create_slot(slot_date=slot_date, slot_time=slot_time)
    except sqlite3.IntegrityError:
        await message.answer("Такий слот уже існує. Введіть іншу дату або час.")
        return

    await message.answer(
        f"✅ Слот створено\n\n"
        f"ID: {slot_id}\n"
        f"Дата: {slot_date}\n"
        f"Час: {slot_time}",
        reply_markup=admin_menu_keyboard(),
    )

    await state.clear()


@router.callback_query(lambda c: c.data == "admin_list_available_slots")
async def admin_list_available_slots(callback: CallbackQuery):
    slots = admin_get_available_slots()

    if not slots:
        await callback.message.edit_text("Немає доступних слотів.")
        await callback.answer()
        return

    lines = ["📅 Доступні слоти:\n"]
    for slot in slots:
        lines.append(
            f"ID {slot['id']} — {slot['slot_date']} {slot['slot_time']} [{slot['status']}]"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_slots_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_list_all_slots")
async def admin_list_all_slots(callback: CallbackQuery):
    slots = admin_get_all_slots()

    if not slots:
        await callback.message.edit_text("Слотів поки немає.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "🗂 Всі слоти:\n\nНатисніть на конкретний слот нижче:",
        reply_markup=_all_slots_keyboard(slots),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_slot_view:"))
async def admin_slot_view(callback: CallbackQuery):
    slot_id = int(callback.data.split(":", 1)[1])
    slot = get_slot_details(slot_id)

    if not slot:
        await callback.message.edit_text("Слот не знайдено.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Слот #{slot['id']}\n\n"
        f"Дата: {slot['slot_date']}\n"
        f"Час: {slot['slot_time']}\n"
        f"Статус: {slot['status']}\n"
        f"Створено: {slot['created_at']}",
        reply_markup=admin_slot_actions_keyboard(slot['id'], slot['status']),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_block_slot:"))
async def admin_block_slot_handler(callback: CallbackQuery):
    slot_id = int(callback.data.split(":", 1)[1])
    slot = get_slot_details(slot_id)

    if not slot:
        await callback.message.edit_text("Слот не знайдено.")
        await callback.answer()
        return

    if slot["status"] == "booked":
        await callback.answer("Зайнятий слот блокувати не можна", show_alert=True)
        return

    admin_block_slot(slot_id)
    updated_slot = get_slot_details(slot_id)

    await callback.message.edit_text(
        f"Слот #{updated_slot['id']}\n\n"
        f"Дата: {updated_slot['slot_date']}\n"
        f"Час: {updated_slot['slot_time']}\n"
        f"Статус: {updated_slot['status']}\n"
        f"Створено: {updated_slot['created_at']}",
        reply_markup=admin_slot_actions_keyboard(updated_slot['id'], updated_slot['status']),
    )
    await callback.answer("Слот заблоковано")


@router.callback_query(lambda c: c.data.startswith("admin_unblock_slot:"))
async def admin_unblock_slot_handler(callback: CallbackQuery):
    slot_id = int(callback.data.split(":", 1)[1])
    slot = get_slot_details(slot_id)

    if not slot:
        await callback.message.edit_text("Слот не знайдено.")
        await callback.answer()
        return

    if slot["status"] == "booked":
        await callback.answer("Зайнятий слот не можна розблокувати вручну", show_alert=True)
        return

    admin_unblock_slot(slot_id)
    updated_slot = get_slot_details(slot_id)

    await callback.message.edit_text(
        f"Слот #{updated_slot['id']}\n\n"
        f"Дата: {updated_slot['slot_date']}\n"
        f"Час: {updated_slot['slot_time']}\n"
        f"Статус: {updated_slot['status']}\n"
        f"Створено: {updated_slot['created_at']}",
        reply_markup=admin_slot_actions_keyboard(updated_slot['id'], updated_slot['status']),
    )
    await callback.answer("Слот розблоковано")


@router.callback_query(lambda c: c.data.startswith("admin_delete_slot:"))
async def admin_delete_slot_handler(callback: CallbackQuery):
    slot_id = int(callback.data.split(":", 1)[1])
    slot = get_slot_details(slot_id)

    if not slot:
        await callback.message.edit_text("Слот не знайдено.")
        await callback.answer()
        return

    if slot["status"] == "booked":
        await callback.answer("Зайнятий слот видаляти не можна", show_alert=True)
        return

    admin_delete_slot(slot_id)

    await callback.message.edit_text(
        "🗑 Слот видалено.",
        reply_markup=admin_slots_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_list_appointments")
async def admin_list_appointments(callback: CallbackQuery):
    appointments = get_bookings_list()

    if not appointments:
        await callback.message.edit_text(
            "Записів поки немає.",
            reply_markup=admin_panel_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "📋 Всі записи:",
        reply_markup=appointments_list_keyboard(appointments),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_list_today_appointments")
async def admin_list_today_appointments(callback: CallbackQuery):
    appointments = get_todays_bookings()

    if not appointments:
        await callback.message.edit_text(
            "На сьогодні записів немає.",
            reply_markup=admin_panel_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "📅 Записи на сьогодні:",
        reply_markup=appointments_list_keyboard(appointments),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_appointment_view:"))
async def admin_appointment_view(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":", 1)[1])
    booking = get_booking_details(appointment_id)

    if not booking:
        await callback.message.edit_text(
            "Запис не знайдено.",
            reply_markup=admin_panel_keyboard(),
        )
        await callback.answer()
        return

    calendar_url = build_google_calendar_url(booking)

    await callback.message.edit_text(
        format_appointment_details(booking),
        reply_markup=appointment_actions_keyboard(
            booking["id"],
            booking["status"],
            calendar_url=calendar_url,
        ),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_confirm_appointment:"))
async def admin_confirm_appointment(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":", 1)[1])
    booking = get_booking_details(appointment_id)

    if not booking:
        await callback.message.edit_text("Запис не знайдено.")
        await callback.answer()
        return

    admin_update_booking_status(appointment_id, "confirmed")
    updated_booking = get_booking_details(appointment_id)
    calendar_url = build_google_calendar_url(updated_booking)

    await callback.message.edit_text(
        format_appointment_details(updated_booking),
        reply_markup=appointment_actions_keyboard(
            updated_booking["id"],
            updated_booking["status"],
            calendar_url=calendar_url,
        ),
    )

    try:
        await callback.bot.send_message(
            chat_id=updated_booking["telegram_user_id"],
            text=(
                "✅ Ваш запис підтверджено.\n\n"
                f"Дата: {updated_booking['slot_date']}\n"
                f"Час: {updated_booking['slot_time']}\n"
                f"Статус: {updated_booking['status']}\n\n"
                "Тепер ви можете додати запис у календар."
            ),
            reply_markup=patient_confirmed_notification_keyboard(calendar_url),
        )
    except Exception:
        pass

    await callback.answer("Запис підтверджено")


@router.callback_query(lambda c: c.data.startswith("admin_cancel_appointment:"))
async def admin_cancel_appointment(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":", 1)[1])
    booking = get_booking_details(appointment_id)

    if not booking:
        await callback.message.edit_text("Запис не знайдено.")
        await callback.answer()
        return

    admin_update_booking_status(appointment_id, "cancelled")
    updated_booking = get_booking_details(appointment_id)
    calendar_url = build_google_calendar_url(updated_booking)

    await callback.message.edit_text(
        format_appointment_details(updated_booking),
        reply_markup=appointment_actions_keyboard(
            updated_booking["id"],
            updated_booking["status"],
            calendar_url=calendar_url,
        ),
    )

    try:
        await callback.bot.send_message(
            chat_id=updated_booking["telegram_user_id"],
            text=(
                "❌ Ваш запис було скасовано.\n\n"
                f"Дата: {updated_booking['slot_date']}\n"
                f"Час: {updated_booking['slot_time']}\n"
                "Якщо потрібно, створіть новий запис."
            ),
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        pass

    await callback.answer("Запис скасовано")


@router.callback_query(lambda c: c.data.startswith("admin_complete_appointment:"))
async def admin_complete_appointment(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":", 1)[1])
    booking = get_booking_details(appointment_id)

    if not booking:
        await callback.message.edit_text("Запис не знайдено.")
        await callback.answer()
        return

    admin_update_booking_status(appointment_id, "completed")
    updated_booking = get_booking_details(appointment_id)
    calendar_url = build_google_calendar_url(updated_booking)

    await callback.message.edit_text(
        format_appointment_details(updated_booking),
        reply_markup=appointment_actions_keyboard(
            updated_booking["id"],
            updated_booking["status"],
            calendar_url=calendar_url,
        ),
    )
    await callback.answer("Запис завершено")


@router.callback_query(lambda c: c.data.startswith("admin_delete_appointment:"))
async def admin_delete_appointment_handler(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":", 1)[1])
    booking = get_booking_details(appointment_id)

    if not booking:
        await callback.message.edit_text("Запис не знайдено.")
        await callback.answer()
        return

    admin_delete_booking(appointment_id)

    await callback.message.edit_text(
        "🗑 Запис видалено.",
        reply_markup=admin_panel_keyboard(),
    )
    await callback.answer("Запис видалено")