# Головний файл запуску
import asyncio
from aiogram import Bot, Dispatcher
from handlers import router
from config import ADMINS
import os

async def main():
    global bot
    token = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        print("token error")
        exit()
    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
