import sqlite3
from contextlib import closing
from typing import Optional

from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def make_client_code(patient_id: int) -> str:
    return f"CL-{patient_id:06d}"


async def init_db():
    with closing(get_connection()) as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_code TEXT UNIQUE,
            telegram_user_id INTEGER NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            phone TEXT,
            age INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_date TEXT NOT NULL,
            slot_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(slot_date, slot_time)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            slot_id INTEGER NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP NULL,
            cancelled_at TIMESTAMP NULL,
            completed_at TIMESTAMP NULL,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (slot_id) REFERENCES time_slots (id)
        )
        """)

        conn.commit()


def get_patient_by_telegram_user_id(telegram_user_id: int) -> Optional[sqlite3.Row]:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM patients
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        )
        return cursor.fetchone()


def get_patient_by_id(patient_id: int) -> Optional[sqlite3.Row]:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM patients
            WHERE id = ?
            """,
            (patient_id,),
        )
        return cursor.fetchone()


def create_patient(
    telegram_user_id: int,
    full_name: str,
    phone: str | None = None,
    age: int | None = None,
) -> int:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO patients (
                telegram_user_id,
                full_name,
                phone,
                age
            )
            VALUES (?, ?, ?, ?)
            """,
            (telegram_user_id, full_name, phone, age),
        )
        patient_id = cursor.lastrowid

        client_code = make_client_code(patient_id)
        cursor.execute(
            """
            UPDATE patients
            SET client_code = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (client_code, patient_id),
        )

        conn.commit()
        return patient_id


def update_patient(
    patient_id: int,
    full_name: str,
    phone: str | None = None,
    age: int | None = None,
) -> None:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE patients
            SET
                full_name = ?,
                phone = ?,
                age = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (full_name, phone, age, patient_id),
        )
        conn.commit()


def create_time_slot(slot_date: str, slot_time: str, status: str = "available") -> int:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO time_slots (slot_date, slot_time, status)
            VALUES (?, ?, ?)
            """,
            (slot_date, slot_time, status),
        )
        conn.commit()
        return cursor.lastrowid


def get_available_dates():
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT slot_date
            FROM time_slots
            WHERE status = 'available'
            ORDER BY slot_date ASC
            """
        )
        return cursor.fetchall()


def get_available_slots_by_date(slot_date: str):
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, slot_date, slot_time, status
            FROM time_slots
            WHERE slot_date = ? AND status = 'available'
            ORDER BY slot_time ASC
            """,
            (slot_date,),
        )
        return cursor.fetchall()


def get_slot_by_id(slot_id: int) -> Optional[sqlite3.Row]:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM time_slots
            WHERE id = ?
            """,
            (slot_id,),
        )
        return cursor.fetchone()


def get_all_slots():
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, slot_date, slot_time, status, created_at
            FROM time_slots
            ORDER BY slot_date ASC, slot_time ASC
            """
        )
        return cursor.fetchall()


def get_available_slots():
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, slot_date, slot_time, status, created_at
            FROM time_slots
            WHERE status = 'available'
            ORDER BY slot_date ASC, slot_time ASC
            """
        )
        return cursor.fetchall()


def update_time_slot_status(slot_id: int, status: str) -> None:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE time_slots
            SET status = ?
            WHERE id = ?
            """,
            (status, slot_id),
        )
        conn.commit()


def delete_time_slot(slot_id: int) -> None:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM time_slots
            WHERE id = ?
              AND status != 'booked'
            """,
            (slot_id,),
        )
        conn.commit()


def delete_appointment(appointment_id: int) -> None:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT slot_id
            FROM appointments
            WHERE id = ?
            """,
            (appointment_id,),
        )
        row = cursor.fetchone()

        if row:
            cursor.execute(
                """
                UPDATE time_slots
                SET status = 'available'
                WHERE id = ?
                """,
                (row["slot_id"],),
            )

        cursor.execute(
            """
            DELETE FROM appointments
            WHERE id = ?
            """,
            (appointment_id,),
        )
        conn.commit()


def create_appointment(
    patient_id: int,
    slot_id: int,
    notes: str | None = None,
    status: str = "pending",
) -> int:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO appointments (patient_id, slot_id, status, notes)
            VALUES (?, ?, ?, ?)
            """,
            (patient_id, slot_id, status, notes),
        )
        conn.commit()
        return cursor.lastrowid


def update_appointment_status(appointment_id: int, status: str) -> None:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()

        if status == "confirmed":
            cursor.execute(
                """
                UPDATE appointments
                SET status = ?, confirmed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, appointment_id),
            )
        elif status == "cancelled":
            cursor.execute(
                """
                UPDATE appointments
                SET status = ?, cancelled_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, appointment_id),
            )
            cursor.execute(
                """
                UPDATE time_slots
                SET status = 'available'
                WHERE id = (
                    SELECT slot_id
                    FROM appointments
                    WHERE id = ?
                )
                """,
                (appointment_id,),
            )
        elif status == "completed":
            cursor.execute(
                """
                UPDATE appointments
                SET status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, appointment_id),
            )
        else:
            cursor.execute(
                """
                UPDATE appointments
                SET status = ?
                WHERE id = ?
                """,
                (status, appointment_id),
            )

        conn.commit()


def get_appointment_by_id(appointment_id: int) -> Optional[sqlite3.Row]:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.patient_id,
                a.slot_id,
                a.status,
                a.notes,
                a.created_at,
                a.confirmed_at,
                a.cancelled_at,
                a.completed_at,
                p.client_code,
                p.full_name,
                p.phone,
                p.age,
                p.telegram_user_id,
                ts.slot_date,
                ts.slot_time,
                ts.status AS slot_status
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            JOIN time_slots ts ON ts.id = a.slot_id
            WHERE a.id = ?
            """,
            (appointment_id,),
        )
        return cursor.fetchone()


def get_all_appointments():
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.patient_id,
                a.slot_id,
                a.status,
                a.notes,
                a.created_at,
                a.confirmed_at,
                a.cancelled_at,
                a.completed_at,
                p.client_code,
                p.full_name,
                p.phone,
                p.age,
                p.telegram_user_id,
                ts.slot_date,
                ts.slot_time,
                ts.status AS slot_status
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            JOIN time_slots ts ON ts.id = a.slot_id
            ORDER BY ts.slot_date, ts.slot_time
            """
        )
        return cursor.fetchall()


def get_todays_appointments():
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.patient_id,
                a.slot_id,
                a.status,
                a.notes,
                a.created_at,
                a.confirmed_at,
                a.cancelled_at,
                a.completed_at,
                p.client_code,
                p.full_name,
                p.phone,
                p.age,
                p.telegram_user_id,
                ts.slot_date,
                ts.slot_time,
                ts.status AS slot_status
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            JOIN time_slots ts ON ts.id = a.slot_id
            WHERE ts.slot_date = date('now', 'localtime')
            ORDER BY ts.slot_time
            """
        )
        return cursor.fetchall()


def get_patient_appointments_by_telegram_user_id(telegram_user_id: int):
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.patient_id,
                a.slot_id,
                a.status,
                a.notes,
                a.created_at,
                a.confirmed_at,
                a.cancelled_at,
                a.completed_at,
                p.client_code,
                p.full_name,
                p.phone,
                p.age,
                p.telegram_user_id,
                ts.slot_date,
                ts.slot_time,
                ts.status AS slot_status
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            JOIN time_slots ts ON ts.id = a.slot_id
            WHERE p.telegram_user_id = ?
            ORDER BY ts.slot_date, ts.slot_time
            """,
            (telegram_user_id,),
        )
        return cursor.fetchall()


def get_active_patient_appointments_by_telegram_user_id(telegram_user_id: int):
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.patient_id,
                a.slot_id,
                a.status,
                a.notes,
                a.created_at,
                a.confirmed_at,
                a.cancelled_at,
                a.completed_at,
                p.client_code,
                p.full_name,
                p.phone,
                p.age,
                p.telegram_user_id,
                ts.slot_date,
                ts.slot_time,
                ts.status AS slot_status
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            JOIN time_slots ts ON ts.id = a.slot_id
            WHERE p.telegram_user_id = ?
              AND a.status IN ('pending', 'confirmed')
            ORDER BY ts.slot_date, ts.slot_time
            """,
            (telegram_user_id,),
        )
        return cursor.fetchall()


def book_slot_and_create_appointment(
    telegram_user_id: int,
    slot_id: int,
    notes: str | None = None,
    full_name: str | None = None,
    phone: str | None = None,
    age: int | None = None,
) -> int:
    with closing(get_connection()) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM patients
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        )
        patient = cursor.fetchone()

        if patient:
            patient_id = patient["id"]
        else:
            if not full_name:
                raise ValueError("Full name is required for a new patient")

            cursor.execute(
                """
                INSERT INTO patients (
                    telegram_user_id,
                    full_name,
                    phone,
                    age
                )
                VALUES (?, ?, ?, ?)
                """,
                (telegram_user_id, full_name, phone, age),
            )
            patient_id = cursor.lastrowid
            client_code = make_client_code(patient_id)

            cursor.execute(
                """
                UPDATE patients
                SET client_code = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (client_code, patient_id),
            )

        cursor.execute(
            """
            SELECT *
            FROM time_slots
            WHERE id = ?
            """,
            (slot_id,),
        )
        slot = cursor.fetchone()

        if not slot:
            raise ValueError("Slot not found")

        if slot["status"] != "available":
            raise ValueError("Slot is no longer available")

        cursor.execute(
            """
            UPDATE time_slots
            SET status = 'booked'
            WHERE id = ?
            """,
            (slot_id,),
        )

        cursor.execute(
            """
            INSERT INTO appointments (patient_id, slot_id, status, notes)
            VALUES (?, ?, 'pending', ?)
            """,
            (patient_id, slot_id, notes),
        )

        appointment_id = cursor.lastrowid
        conn.commit()
        return appointment_id


def seed_demo_slots():
    demo_slots = [
        ("2026-03-12", "10:00"),
        ("2026-03-12", "11:00"),
        ("2026-03-12", "14:00"),
        ("2026-03-13", "09:30"),
        ("2026-03-13", "12:00"),
        ("2026-03-14", "15:30"),
    ]

    with closing(get_connection()) as conn:
        cursor = conn.cursor()

        for slot_date, slot_time in demo_slots:
            cursor.execute(
                """
                INSERT OR IGNORE INTO time_slots (slot_date, slot_time, status)
                VALUES (?, ?, 'available')
                """,
                (slot_date, slot_time),
            )

        conn.commit()