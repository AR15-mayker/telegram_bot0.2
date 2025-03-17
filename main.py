import os
import asyncio
from aiogram import Bot, Dispatcher
from dotenv import find_dotenv, load_dotenv
from loguru import logger
from handlers.user_private import dp
from utils.utils import send_random_joke

load_dotenv(find_dotenv())
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("Не удалось загрузить TOKEN из .env")

logger.add("bot.log", rotation="10 MB", level="INFO")
logger.info("Бот запущен")

bot = Bot(token=TOKEN)

async def main():
    asyncio.create_task(send_random_joke())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
