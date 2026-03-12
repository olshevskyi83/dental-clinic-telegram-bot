import asyncio

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from app.database.db import init_db, seed_demo_slots
from app.handlers.admin import router as admin_router
from app.handlers.booking import router as booking_router
from app.handlers.my_appointments import router as my_appointments_router
from app.handlers.start import router as start_router


async def main():
    await init_db()
    seed_demo_slots()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(booking_router)
    dp.include_router(my_appointments_router)

    print("Bot started successfully")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())