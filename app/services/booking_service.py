from datetime import datetime, timedelta
from urllib.parse import quote

from app.database.db import (
    book_slot_and_create_appointment,
    create_time_slot,
    delete_appointment,
    delete_time_slot,
    get_all_appointments,
    get_all_slots,
    get_appointment_by_id,
    get_available_dates,
    get_available_slots,
    get_available_slots_by_date,
    get_patient_appointments_by_telegram_user_id,
    get_patient_by_telegram_user_id,
    get_slot_by_id,
    get_todays_appointments,
    get_active_patient_appointments_by_telegram_user_id,
    update_appointment_status,
    update_time_slot_status,
)


def get_free_dates():
    return get_available_dates()


def get_free_slots_for_date(slot_date: str):
    return get_available_slots_by_date(slot_date)


def get_slot_details(slot_id: int):
    return get_slot_by_id(slot_id)


def get_patient_profile(telegram_user_id: int):
    return get_patient_by_telegram_user_id(telegram_user_id)


def save_booking(
    telegram_user_id: int,
    slot_id: int,
    notes: str | None = None,
    full_name: str | None = None,
    phone: str | None = None,
    age: int | None = None,
) -> int:
    if full_name:
        full_name = full_name.strip()

    if notes:
        notes = notes.strip()

    if phone:
        phone = phone.strip()

    return book_slot_and_create_appointment(
        telegram_user_id=telegram_user_id,
        slot_id=slot_id,
        notes=notes,
        full_name=full_name,
        phone=phone,
        age=age,
    )


def get_booking_details(appointment_id: int):
    return get_appointment_by_id(appointment_id)


def get_bookings_list():
    return get_all_appointments()


def get_todays_bookings():
    return get_todays_appointments()


def get_my_appointments(telegram_user_id: int):
    return get_patient_appointments_by_telegram_user_id(telegram_user_id)


def get_my_active_appointments(telegram_user_id: int):
    return get_active_patient_appointments_by_telegram_user_id(telegram_user_id)


def can_patient_cancel_appointment(booking) -> bool:
    if not booking:
        return False

    if booking["status"] not in ("pending", "confirmed"):
        return False

    visit_dt = datetime.strptime(
        f"{booking['slot_date']} {booking['slot_time']}",
        "%Y-%m-%d %H:%M"
    )
    now = datetime.now()
    return (visit_dt - now).total_seconds() >= 24 * 60 * 60


def build_google_calendar_url(booking) -> str:
    start_dt = datetime.strptime(
        f"{booking['slot_date']} {booking['slot_time']}",
        "%Y-%m-%d %H:%M"
    )
    end_dt = start_dt + timedelta(hours=1)

    start_str = start_dt.strftime("%Y%m%dT%H%M%S")
    end_str = end_dt.strftime("%Y%m%dT%H%M%S")

    title = quote("Dental Clinic Appointment")
    details = quote(booking["notes"] if booking["notes"] else "Dental clinic visit")

    return (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={title}"
        f"&dates={start_str}/{end_str}"
        f"&details={details}"
    )


def patient_cancel_appointment(appointment_id: int):
    update_appointment_status(appointment_id, "cancelled")


def admin_update_booking_status(appointment_id: int, status: str):
    update_appointment_status(appointment_id, status)


def admin_delete_booking(appointment_id: int):
    delete_appointment(appointment_id)


def admin_create_slot(slot_date: str, slot_time: str) -> int:
    return create_time_slot(slot_date=slot_date, slot_time=slot_time, status="available")


def admin_get_all_slots():
    return get_all_slots()


def admin_get_available_slots():
    return get_available_slots()


def admin_block_slot(slot_id: int):
    update_time_slot_status(slot_id, "blocked")


def admin_unblock_slot(slot_id: int):
    update_time_slot_status(slot_id, "available")


def admin_delete_slot(slot_id: int):
    delete_time_slot(slot_id)