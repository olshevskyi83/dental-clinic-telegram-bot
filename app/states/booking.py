from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    waiting_for_slot = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_age = State()
    waiting_for_notes = State()
    waiting_for_confirmation = State()