from aiogram.fsm.state import State, StatesGroup


class AdminSlotStates(StatesGroup):
    waiting_for_slot_date = State()
    waiting_for_slot_time = State()