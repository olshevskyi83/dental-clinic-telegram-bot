from aiogram import Router
from aiogram.types import CallbackQuery, Message

from app.keyboards.appointments_kb import (
    cancel_appointments_keyboard,
    cancel_confirm_keyboard,
    my_appointment_actions_keyboard,
    my_appointments_keyboard,
)
from app.keyboards.reply import main_menu_keyboard
from app.services.booking_service import (
    build_google_calendar_url,
    can_patient_cancel_appointment,
    get_booking_details,
    get_my_active_appointments,
    get_my_appointments,
    patient_cancel_appointment,
)

router = Router()


def format_my_booking(booking) -> str:
    notes_text = booking["notes"] if booking["notes"] else "Не вказано"

    text = (
        f"Ваш запис #{booking['id']}\n\n"
        f"Клієнт: {booking['client_code']}\n"
        f"Дата: {booking['slot_date']}\n"
        f"Час: {booking['slot_time']}\n"
        f"Статус: {booking['status']}\n"
        f"Коментар: {notes_text}"
    )

    if booking["status"] == "pending":
        text += "\n\nОчікує підтвердження адміністратором."
    elif booking["status"] == "confirmed":
        text += "\n\nЗапис підтверджено. Можна додати в календар."

    return text


@router.message(lambda message: message.text == "Мої записи")
async def my_appointments(message: Message):
    appointments = get_my_appointments(message.from_user.id)

    if not appointments:
        await message.answer(
            "У вас поки немає записів.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        "Ваші записи:",
        reply_markup=my_appointments_keyboard(appointments),
    )


@router.callback_query(lambda c: c.data == "my_appointments_list")
async def my_appointments_list(callback: CallbackQuery):
    appointments = get_my_appointments(callback.from_user.id)

    if not appointments:
        await callback.message.edit_text("У вас поки немає записів.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "Ваші записи:",
        reply_markup=my_appointments_keyboard(appointments),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("my_appointment_view:"))
async def my_appointment_view(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":", 1)[1])
    booking = get_booking_details(appointment_id)

    if not booking or booking["telegram_user_id"] != callback.from_user.id:
        await callback.answer("Запис не знайдено", show_alert=True)
        return

    calendar_url = None
    if booking["status"] == "confirmed":
        calendar_url = build_google_calendar_url(booking)

    await callback.message.edit_text(
        format_my_booking(booking),
        reply_markup=my_appointment_actions_keyboard(
            appointment_id=appointment_id,
            status=booking["status"],
            calendar_url=calendar_url,
        ),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("my_appointment_cancel:"))
async def my_appointment_cancel(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":", 1)[1])
    booking = get_booking_details(appointment_id)

    if not booking or booking["telegram_user_id"] != callback.from_user.id:
        await callback.answer("Запис не знайдено", show_alert=True)
        return

    await callback.message.edit_text(
        f"{format_my_booking(booking)}\n\n"
        f"Ви дійсно хочете відмінити цей запис?",
        reply_markup=cancel_confirm_keyboard(appointment_id),
    )
    await callback.answer()


@router.message(lambda message: message.text == "Відмінити запис")
async def cancel_my_appointment_start(message: Message):
    appointments = get_my_active_appointments(message.from_user.id)

    if not appointments:
        await message.answer(
            "У вас немає активних записів для скасування.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        "Оберіть запис, який хочете відмінити:",
        reply_markup=cancel_appointments_keyboard(appointments),
    )


@router.callback_query(lambda c: c.data.startswith("cancel_pick:"))
async def cancel_pick(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":", 1)[1])
    booking = get_booking_details(appointment_id)

    if not booking or booking["telegram_user_id"] != callback.from_user.id:
        await callback.answer("Запис не знайдено", show_alert=True)
        return

    await callback.message.edit_text(
        f"{format_my_booking(booking)}\n\n"
        f"Ви дійсно хочете відмінити цей запис?",
        reply_markup=cancel_confirm_keyboard(appointment_id),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("cancel_confirm:"))
async def cancel_confirm(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":", 1)[1])
    booking = get_booking_details(appointment_id)

    if not booking or booking["telegram_user_id"] != callback.from_user.id:
        await callback.answer("Запис не знайдено", show_alert=True)
        return

    if not can_patient_cancel_appointment(booking):
        await callback.message.edit_text(
            "Ви можете відмінити запис не пізніше ніж за 24 години до візиту.\n\n"
            "Якщо цей строк уже минув — будь ласка, зателефонуйте в клініку."
        )
        await callback.answer()
        return

    patient_cancel_appointment(appointment_id)
    updated_booking = get_booking_details(appointment_id)

    await callback.message.edit_text(
        f"✅ Запис скасовано.\n\n{format_my_booking(updated_booking)}"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_back_to_list")
async def cancel_back_to_list(callback: CallbackQuery):
    appointments = get_my_active_appointments(callback.from_user.id)

    if not appointments:
        await callback.message.edit_text("У вас немає активних записів для скасування.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "Оберіть запис, який хочете відмінити:",
        reply_markup=cancel_appointments_keyboard(appointments),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_close")
async def cancel_close(callback: CallbackQuery):
    await callback.message.edit_text("Операцію скасовано.")
    await callback.answer()


@router.callback_query(lambda c: c.data == "my_appointments_close")
async def my_appointments_close(callback: CallbackQuery):
    await callback.message.edit_text("Список закрито.")
    await callback.answer()