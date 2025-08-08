# Головний файл запуску
import asyncio
from aiogram import Bot, Dispatcher
from handlers import router
from config import ADMINS

# Введення токену при запуску
def input_token():
    print("============== ЗАПУСК БОТА ==============")
    print("Введи токен бота:")
    return input("> ")

async def main():
    global bot
    token = input_token()
    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())