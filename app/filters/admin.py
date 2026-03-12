from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config import ADMIN_IDS


class IsAdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if not user:
            return False
        return user.id in ADMIN_IDS