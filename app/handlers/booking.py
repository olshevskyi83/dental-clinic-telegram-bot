from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.confirm_kb import confirm_booking_keyboard
from app.keyboards.reply import main_menu_keyboard
from app.keyboards.slots_kb import available_dates_keyboard, available_times_keyboard
from app.services.booking_service import (
    get_booking_details,
    get_free_dates,
    get_free_slots_for_date,
    get_patient_profile,
    get_slot_details,
    save_booking,
)
from app.states.booking import BookingStates

router = Router()


def is_valid_phone(phone_text: str) -> bool:
    cleaned = phone_text.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def normalize_phone(phone_text: str) -> str:
    return " ".join(phone_text.strip().split())


def is_valid_age(age_text: str) -> bool:
    if not age_text.isdigit():
        return False
    age = int(age_text)
    return 1 <= age <= 120


@router.message(lambda message: message.text == "Записатися на прийом")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()

    dates = get_free_dates()

    if not dates:
        await message.answer(
            "Наразі немає доступних слотів для запису.\n"
            "Спробуйте пізніше.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.set_state(BookingStates.waiting_for_slot)

    await message.answer(
        "Оберіть доступну дату:",
        reply_markup=available_dates_keyboard(dates),
    )


@router.callback_query(lambda c: c.data.startswith("slot_date:"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    selected_date = callback.data.split(":", 1)[1]

    slots = get_free_slots_for_date(selected_date)

    if not slots:
        await callback.message.edit_text(
            "На цю дату вже немає доступного часу. Оберіть іншу дату:",
            reply_markup=available_dates_keyboard(get_free_dates()),
        )
        await callback.answer()
        return

    await state.update_data(selected_date=selected_date)

    await callback.message.edit_text(
        f"Оберіть час на {selected_date}:",
        reply_markup=available_times_keyboard(slots, selected_date),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_dates")
async def back_to_dates(callback: CallbackQuery, state: FSMContext):
    dates = get_free_dates()

    if not dates:
        await callback.message.edit_text("Наразі немає доступних слотів.")
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_text(
        "Оберіть доступну дату:",
        reply_markup=available_dates_keyboard(dates),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("slot_pick:"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    try:
        slot_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Некоректний слот", show_alert=True)
        return

    slot = get_slot_details(slot_id)

    if not slot or slot["status"] != "available":
        await callback.message.edit_text(
            "Цей слот вже недоступний. Оберіть інший.",
            reply_markup=available_dates_keyboard(get_free_dates()),
        )
        await state.clear()
        await callback.answer()
        return

    patient = get_patient_profile(callback.from_user.id)

    await state.update_data(
        slot_id=slot["id"],
        slot_date=slot["slot_date"],
        slot_time=slot["slot_time"],
        is_existing_patient=bool(patient),
    )

    if patient:
        await state.update_data(
            patient_id=patient["id"],
            client_code=patient["client_code"],
            full_name=patient["full_name"],
            phone=patient["phone"],
            age=patient["age"],
        )
        await state.set_state(BookingStates.waiting_for_notes)

        phone_text = patient["phone"] if patient["phone"] else "Не вказано"
        age_text = patient["age"] if patient["age"] is not None else "Не вказано"

        await callback.message.edit_text(
            f"Ви обрали слот:\n\n"
            f"Дата: {slot['slot_date']}\n"
            f"Час: {slot['slot_time']}\n\n"
            f"Ваш профіль знайдено:\n"
            f"Клієнт: {patient['client_code']}\n"
            f"Ім'я: {patient['full_name']}\n"
            f"Телефон: {phone_text}\n"
            f"Вік: {age_text}\n\n"
            f"Тепер опишіть коротко проблему або побажання.\n"
            f"Якщо не хочете — напишіть: -"
        )
        await callback.answer()
        return

    await state.set_state(BookingStates.waiting_for_name)

    await callback.message.edit_text(
        f"Ви обрали слот:\n\n"
        f"Дата: {slot['slot_date']}\n"
        f"Час: {slot['slot_time']}\n\n"
        f"Схоже, ви записуєтесь вперше.\n"
        f"Введіть ваше ім'я та прізвище:"
    )
    await callback.answer()


@router.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()

    if len(name) < 2:
        await message.answer("Ім'я занадто коротке. Введіть нормальне ім'я.")
        return

    await state.update_data(full_name=name)
    await state.set_state(BookingStates.waiting_for_phone)

    await message.answer(
        "Введіть номер телефону.\n"
        "Наприклад: +49 155 12345678"
    )


@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = (message.text or "").strip()

    if not is_valid_phone(phone):
        await message.answer(
            "Некоректний номер телефону.\n"
            "Приклад: +49 155 12345678"
        )
        return

    phone = normalize_phone(phone)
    await state.update_data(phone=phone)
    await state.set_state(BookingStates.waiting_for_age)

    await message.answer("Введіть ваш вік числом. Наприклад: 34")


@router.message(BookingStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    age_text = (message.text or "").strip()

    if not is_valid_age(age_text):
        await message.answer("Некоректний вік. Введіть число від 1 до 120.")
        return

    await state.update_data(age=int(age_text))
    await state.set_state(BookingStates.waiting_for_notes)

    await message.answer(
        "Опишіть коротко проблему або побажання.\n"
        "Наприклад: болить зуб, консультація, чистка.\n\n"
        "Якщо не хочете — напишіть: -"
    )


@router.message(BookingStates.waiting_for_notes)
async def process_notes(message: Message, state: FSMContext):
    notes = (message.text or "").strip()

    if notes == "-":
        notes = None

    await state.update_data(notes=notes)
    data = await state.get_data()

    notes_text = notes if notes else "Не вказано"
    phone_text = data.get("phone") or "Не вказано"
    age_text = data.get("age") if data.get("age") is not None else "Не вказано"
    client_code = data.get("client_code") or "Буде присвоєно після створення"

    await state.set_state(BookingStates.waiting_for_confirmation)

    await message.answer(
        f"Перевірте дані запису:\n\n"
        f"Клієнт: {client_code}\n"
        f"Пацієнт: {data['full_name']}\n"
        f"Телефон: {phone_text}\n"
        f"Вік: {age_text}\n"
        f"Дата: {data['slot_date']}\n"
        f"Час: {data['slot_time']}\n"
        f"Коментар: {notes_text}",
        reply_markup=confirm_booking_keyboard(),
    )


@router.callback_query(lambda c: c.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if not data:
        await callback.answer(
            "Дані запису не знайдено. Почніть заново.",
            show_alert=True,
        )
        return

    slot_id = data.get("slot_id")
    if not slot_id:
        await callback.answer(
            "Слот не знайдено. Почніть заново.",
            show_alert=True,
        )
        await state.clear()
        return

    notes = data.get("notes")
    is_existing_patient = data.get("is_existing_patient", False)

    try:
        if is_existing_patient:
            appointment_id = save_booking(
                telegram_user_id=callback.from_user.id,
                slot_id=slot_id,
                notes=notes,
            )
        else:
            appointment_id = save_booking(
                telegram_user_id=callback.from_user.id,
                slot_id=slot_id,
                notes=notes,
                full_name=data.get("full_name"),
                phone=data.get("phone"),
                age=data.get("age"),
            )
    except ValueError as e:
        await callback.message.edit_text(
            f"Не вдалося завершити бронювання: {str(e)}\n\n"
            f"Спробуйте обрати слот ще раз."
        )
        await state.clear()
        await callback.answer()
        return

    booking = get_booking_details(appointment_id)
    notes_text = booking["notes"] if booking["notes"] else "Не вказано"
    phone_text = booking["phone"] if booking["phone"] else "Не вказано"
    age_text = booking["age"] if booking["age"] is not None else "Не вказано"

    await callback.message.edit_text(
        f"✅ Запис підтверджено\n\n"
        f"Запис №: {booking['id']}\n"
        f"Клієнт: {booking['client_code']}\n"
        f"Пацієнт: {booking['full_name']}\n"
        f"Телефон: {phone_text}\n"
        f"Вік: {age_text}\n"
        f"Дата: {booking['slot_date']}\n"
        f"Час: {booking['slot_time']}\n"
        f"Статус запису: {booking['status']}\n"
        f"Коментар: {notes_text}"
    )

    await callback.message.answer(
        "Щоб створити ще один запис, натисніть кнопку в меню.",
        reply_markup=main_menu_keyboard(),
    )

    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_booking")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❌ Запис скасовано.\n\n"
        "Щоб створити новий запис — натисніть кнопку в меню."
    )

    await callback.message.answer(
        "Головне меню:",
        reply_markup=main_menu_keyboard(),
    )

    await state.clear()
    await callback.answer()