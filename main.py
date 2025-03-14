import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dotenv import find_dotenv, load_dotenv
from datetime import datetime
import sqlite3
from loguru import logger
from bs4 import BeautifulSoup
from random import choice
from dateutil import parser

load_dotenv(find_dotenv())
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = -1002531397827

if not TOKEN or not CHANNEL_ID:
    raise ValueError("Не удалось загрузить TOKEN или CHANNEL_ID из .env")

logger.add("bot.log", rotation="10 MB", level="INFO")
logger.info("Бот запущен")

bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect('events.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    event TEXT NOT NULL
)
''')
conn.commit()

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
                anekdot = "Не удалось получить анекдот"

            await bot.send_message(CHANNEL_ID, f"🎭 *Анекдот дня:*\n\n{anekdot}", parse_mode="Markdown")
            logger.info(f"Опубликован анекдот: {anekdot}")
        except Exception as e:
            logger.error(f"Ошибка при отправке анекдота: {e}")

        await asyncio.sleep(60)

def get_main_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="📅 Добавить событие"))
    keyboard.add(KeyboardButton(text="📋 Показать события"))
    keyboard.add(KeyboardButton(text="❌ Удалить событие"))
    keyboard.add(KeyboardButton(text="🔍 События на дату"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "📅 *Привет! Я бот-календарь.*\n\n"
        "Вот что я умею:\n"
        "➕ *Добавить событие* — просто напиши дату и событие.\n"
        "📋 *Показать все события* — увидишь всё, что запланировано.\n"
        "❌ *Удалить событие* — выбери, что хочешь удалить.\n"
        "🔍 *События на дату* — узнай, что запланировано на конкретный день.\n\n"
        "Используй кнопки ниже или команды!",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "📅 Добавить событие")
async def add_event_button(message: Message):
    await message.answer(
        "📝 *Добавление события*\n\n"
        "Введи дату и событие в формате:\n"
        "`<дата> <событие>`\n\n"
        "*Пример:*\n"
        "`2023-10-15 Встреча с друзьями`",
        parse_mode="Markdown"
    )

@dp.message(lambda message: len(message.text.split()) >= 2 and not message.text.startswith('/'))
async def process_add_event(message: Message):
    try:
        date_part, event = message.text.split(maxsplit=1)
        date = parser.parse(date_part, dayfirst=True).strftime('%Y-%m-%d')
        cursor.execute(
            'INSERT INTO events (date, event) VALUES (?, ?)', 
            (date, event)
        )
        conn.commit()
        await message.answer(
            f"✅ *Событие добавлено!*\n\n"
            f"📅 *Дата:* `{date}`\n"
            f"📝 *Событие:* `{event}`",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    except ValueError:
        await message.answer(
            "❌ *Ошибка!*\n\n"
            "Неверный формат даты.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

@dp.message(lambda message: message.text == "📋 Показать события")
async def show_events_button(message: Message):
    cursor.execute('SELECT date, event FROM events')
    events = cursor.fetchall()
    if not events:
        await message.answer(
            "📅 *Событий пока нет.*\n\n"
            "Добавь новое событие с помощью кнопки «📅 Добавить событие».",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        response = "📅 *Все события:*\n\n" + "\n".join([f"📅 *Дата:* `{date}`\n📝 *Событие:* `{event}`" for date, event in events])
        await message.answer(response, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(lambda message: message.text == "❌ Удалить событие")
async def delete_event_button(message: Message):
    cursor.execute('SELECT date, event FROM events')
    events = cursor.fetchall()
    if not events:
        await message.answer(
            "📅 *Событий пока нет.*\n\n"
            "Добавь новое событие с помощью кнопки «📅 Добавить событие».",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        keyboard = InlineKeyboardBuilder()
        for date, event in events:
            keyboard.add(InlineKeyboardButton(text=f"{date}: {event}", callback_data=f"delete_{date}_{event}"))
        keyboard.adjust(1)
        await message.answer(
            "❌ *Выбери событие для удаления:*",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )

@dp.callback_query(lambda query: query.data.startswith("delete_"))
async def process_delete_event(callback: types.CallbackQuery):
    _, date, event = callback.data.split('_', 2)
    cursor.execute('DELETE FROM events WHERE date = ? AND event = ?', (date, event))
    conn.commit()
    await callback.message.answer(
        f"✅ *Событие удалено!*\n\n"
        f"📅 *Дата:* `{date}`\n"
        f"📝 *Событие:* `{event}`",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(lambda message: message.text == "🔍 События на дату")
async def events_on_date_button(message: Message):
    await message.answer(
        "📅 *Поиск событий на дату*\n\n"
        "Введи дату в любом формате.\n\n"
        "*Пример:*\n"
        "`2023-10-15` или `15 октября 2023`",
        parse_mode="Markdown"
    )

@dp.message(lambda message: len(message.text.split()) == 1 and not message.text.startswith('/'))
async def process_events_on_date(message: Message):
    try:
        date = parser.parse(message.text, dayfirst=True).strftime('%Y-%m-%d')
        cursor.execute('SELECT event FROM events WHERE date = ?', (date,))
        events = cursor.fetchall()
        if not events:
            await message.answer(
                f"📅 *На {date} событий нет.*\n\n"
                "Добавь новое событие с помощью кнопки «📅 Добавить событие».",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
        else:
            response = f"📅 *События на {date}:*\n\n" + "\n".join([f"📝 *Событие:* `{event[0]}`" for event in events])
            await message.answer(response, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    except ValueError:
        await message.answer(
            "❌ *Ошибка!*\n\n"
            "Неверный формат даты. Попробуй ввести дату в другом формате.\n\n"
            "*Пример:*\n"
            "`2023-10-15` или `15 октября 2023`",
            parse_mode="Markdown"
        )

@dp.message()
async def echo(message: Message):
    await message.answer(
        "❓ *Неизвестная команда.*\n\n"
        "Вот что я умею:\n"
        "➕ *Добавить событие* — просто напиши дату и событие.\n"
        "📋 *Показать все события* — увидишь всё, что запланировано.\n"
        "❌ *Удалить событие* — выбери, что хочешь удалить.\n"
        "🔍 *События на дату* — узнай, что запланировано на конкретный день.\n\n"
        "Используй кнопки ниже!",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

async def main():
    asyncio.create_task(send_random_joke())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
