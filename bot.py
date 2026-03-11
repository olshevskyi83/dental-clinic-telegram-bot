import asyncio
import logging
import os
import sqlite3
from contextlib import closing
from datetime import date, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils import executor

# ------------------------------------------------------------
# Telegram Dental Clinic Bot
# aiogram v2 FSM + SQLite appointment booking
# ------------------------------------------------------------
# This bot:
# 1. Greets the user
# 2. Collects patient name and symptoms step-by-step
# 3. Finds the nearest free appointment slot in SQLite
# 4. Books the slot after confirmation
# 5. Does NOT provide medical advice
# ------------------------------------------------------------

API_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
DB_PATH = os.getenv("DB_PATH", "clinic.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class BookingForm(StatesGroup):
    patient_name = State()
    pain_place = State()
    symptoms = State()
    timing = State()
    pain_type = State()
    confirm_booking = State()


def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create appointments table if it does not exist."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                patient_name TEXT,
                symptoms TEXT,
                is_booked INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


def seed_slots(days_ahead: int = 7) -> None:
    """
    Fill the database with slots for the next week.
    Slots per day: 09:00, 10:00, 11:00, 14:00, 15:00
    Existing rows are preserved.
    """
    slots = ["09:00", "10:00", "11:00", "14:00", "15:00"]

    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()

        for offset in range(days_ahead):
            slot_date = (date.today() + timedelta(days=offset)).isoformat()
            for slot_time in slots:
                cursor.execute(
                    "SELECT id FROM appointments WHERE date = ? AND time = ?",
                    (slot_date, slot_time),
                )
                exists = cursor.fetchone()
                if not exists:
                    cursor.execute(
                        """
                        INSERT INTO appointments (date, time, patient_name, symptoms, is_booked)
                        VALUES (?, ?, NULL, NULL, 0)
                        """,
                        (slot_date, slot_time),
                    )

        conn.commit()


def find_nearest_free_slot():
    """Return the nearest available slot as a sqlite Row or None."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, date, time
            FROM appointments
            WHERE is_booked = 0
            ORDER BY date ASC, time ASC
            LIMIT 1
            """
        )
        return cursor.fetchone()


def book_slot(slot_id: int, patient_name: str, symptoms: str) -> bool:
    """
    Book a slot only if it is still free.
    Returns True if booking succeeded.
    """
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE appointments
            SET patient_name = ?, symptoms = ?, is_booked = 1
            WHERE id = ? AND is_booked = 0
            """,
            (patient_name, symptoms, slot_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_yes_no_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    keyboard.add(KeyboardButton("Так"), KeyboardButton("Ні"))
    return keyboard


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Restart dialogue from scratch.
    /start always clears current FSM state.
    """
    await state.finish()

    welcome_text = (
        "Вітаю! Я бот стоматологічної клініки.\n\n"
        "Я можу лише допомогти із записом на прийом.\n"
        "Я не надаю медичних порад і не ставлю діагноз.\n\n"
        "Щоб почати запис, напишіть, будь ласка, ім'я пацієнта."
    )
    await BookingForm.patient_name.set()
    await message.answer(welcome_text, reply_markup=ReplyKeyboardRemove())


@dp.message_handler(commands=["cancel"], state="*")
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Allow user to cancel the current conversation."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Наразі немає активного запису. Напишіть /start, щоб почати.")
        return

    await state.finish()
    await message.answer(
        "Розмову скасовано. Напишіть /start, якщо хочете почати знову.",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message_handler(state=BookingForm.patient_name)
async def process_patient_name(message: types.Message, state: FSMContext):
    patient_name = normalize_text(message.text or "")
    if len(patient_name) < 2:
        await message.answer("Будь ласка, введіть коректне ім'я пацієнта (мінімум 2 символи).")
        return

    await state.update_data(patient_name=patient_name)
    await BookingForm.next()
    await message.answer("Що саме болить? Наприклад: зуб, ясна, щелепа.")


@dp.message_handler(state=BookingForm.pain_place)
async def process_pain_place(message: types.Message, state: FSMContext):
    pain_place = normalize_text(message.text or "")
    if len(pain_place) < 2:
        await message.answer("Опишіть, будь ласка, що саме болить.")
        return

    await state.update_data(pain_place=pain_place)
    await BookingForm.next()
    await message.answer(
        "Які симптоми ви маєте? Наприклад: гострий біль, набряк, кровотеча."
    )


@dp.message_handler(state=BookingForm.symptoms)
async def process_symptoms(message: types.Message, state: FSMContext):
    symptoms = normalize_text(message.text or "")
    if len(symptoms) < 3:
        await message.answer("Будь ласка, опишіть симптоми трохи детальніше.")
        return

    await state.update_data(symptoms=symptoms)
    await BookingForm.next()
    await message.answer(
        "Коли болить? Наприклад: постійно, після їжі, вночі."
    )


@dp.message_handler(state=BookingForm.timing)
async def process_timing(message: types.Message, state: FSMContext):
    timing = normalize_text(message.text or "")
    if len(timing) < 2:
        await message.answer("Будь ласка, уточніть, коли саме болить.")
        return

    await state.update_data(timing=timing)
    await BookingForm.next()
    await message.answer(
        "Як саме болить? Наприклад: гостро, ниюче, пульсуюче."
    )


@dp.message_handler(state=BookingForm.pain_type)
async def process_pain_type(message: types.Message, state: FSMContext):
    pain_type = normalize_text(message.text or "")
    if len(pain_type) < 2:
        await message.answer("Будь ласка, опишіть характер болю.")
        return

    await state.update_data(pain_type=pain_type)
    user_data = await state.get_data()

    full_symptoms = (
        f"Що болить: {user_data['pain_place']}; "
        f"Симптоми: {user_data['symptoms']}; "
        f"Коли болить: {user_data['timing']}; "
        f"Як болить: {pain_type}"
    )
    await state.update_data(full_symptoms=full_symptoms)

    free_slot = find_nearest_free_slot()
    if free_slot is None:
        await state.finish()
        await message.answer(
            "На жаль, зараз немає вільних слотів для запису.\n\n"
            "Ви можете:\n"
            "- написати пізніше\n"
            "- або зв'язатися з адміністратором клініки\n\n"
            "Щоб спробувати знову, напишіть /start"
        )
        return

    await state.update_data(slot_id=free_slot["id"], slot_date=free_slot["date"], slot_time=free_slot["time"])
    await BookingForm.next()

    confirmation_text = (
        "Я знайшов найближчий вільний слот:\n\n"
        f"Дата: {free_slot['date']}\n"
        f"Час: {free_slot['time']}\n"
        f"Пацієнт: {user_data['patient_name']}\n\n"
        "Підтвердити запис?"
    )
    await message.answer(confirmation_text, reply_markup=get_yes_no_keyboard())


@dp.message_handler(lambda message: message.text not in ["Так", "Ні"], state=BookingForm.confirm_booking)
async def process_invalid_confirmation(message: types.Message):
    await message.answer("Будь ласка, оберіть один із варіантів: Так або Ні.")


@dp.message_handler(Text(equals="Ні", ignore_case=True), state=BookingForm.confirm_booking)
async def process_decline_booking(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Добре, запис не підтверджено.\n"
        "Щоб почати заново, напишіть /start",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message_handler(Text(equals="Так", ignore_case=True), state=BookingForm.confirm_booking)
async def process_confirm_booking(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    success = book_slot(
        slot_id=user_data["slot_id"],
        patient_name=user_data["patient_name"],
        symptoms=user_data["full_symptoms"],
    )

    if not success:
        await state.finish()
        await message.answer(
            "На жаль, цей слот щойно став недоступним.\n"
            "Будь ласка, напишіть /start, щоб знайти інший час.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.finish()
    await message.answer(
        "Запис підтверджено ✅\n\n"
        f"Пацієнт: {user_data['patient_name']}\n"
        f"Дата: {user_data['slot_date']}\n"
        f"Час: {user_data['slot_time']}\n\n"
        "Дякуємо! Якщо потрібно створити новий запис, напишіть /start",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message_handler(state="*")
async def fallback_handler(message: types.Message):
    """Catch-all fallback for unexpected input."""
    await message.answer(
        "Я допомагаю лише із записом до стоматологічної клініки.\n"
        "Напишіть /start, щоб почати, або /cancel, щоб скасувати поточну розмову."
    )


async def on_startup(_: Dispatcher):
    init_db()
    seed_slots(days_ahead=7)
    logger.info("Database initialized and slots seeded.")


if __name__ == "__main__":
    if API_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "BOT_TOKEN is not set. Please export BOT_TOKEN or replace the placeholder in bot.py"
        )

    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
