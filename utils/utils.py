import os
import asyncio
import requests
from loguru import logger
from bs4 import BeautifulSoup
from random import choice
from aiogram import Bot
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = -1002531397827

bot = Bot(token=TOKEN)

async def send_random_joke():
    while True:
        try:
            response = requests.get('https://www.anekdot.ru/random/anekdot/')
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                jokes = soup.find_all('div', class_='text')
                if jokes:
                    anekdot = choice(jokes).text.strip()
                else:
                    anekdot = "Не удалось получить анекдот"
            else:
                anekdot = f"Не удалось получить анекдот (статус-код: {response.status_code})"
            
            await bot.send_message(chat_id=CHANNEL_ID, text=f"🎭 *Анекдот дня:*\n\n{anekdot}", parse_mode="Markdown")
            logger.info(f"Опубликован анекдот: {anekdot}")
        except Exception as e:
            logger.error(f"Ошибка при отправке анекдота: {e}")

        await asyncio.sleep(60)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(send_random_joke())
    loop.run_forever()
