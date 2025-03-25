import os
from aiogram import types, Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dateutil import parser
import pytz
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder, InlineKeyboardButton
from datetime import datetime
from loguru import logger
from bs4 import BeautifulSoup
from random import choice
from dateutil import parser
from database.database import conn, cursor
from keyboards.keyboards import get_main_keyboard
from dotenv import load_dotenv, find_dotenv


logger.add(
    "bot.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="10 MB",
    compression="zip",
    level="INFO"
)

load_dotenv(find_dotenv())
TOKEN = os.getenv("TOKEN")
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_cmd(message: Message):
    logger.info(f"User {message.from_user.id} старт бота")
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
    logger.info(f"User {message.from_user.id} добавляет событие'")
    await message.answer(
        "📝 *Добавление события*\n\n"
        "Введи дату и событие в формате:\n"
        "`<дата> <событие>`\n\n"
        "*Пример:*\n"
        "• 15-10-2023 14:30 Встреча\n"
        "• 15.10.2023 День рождения\n"
        "• 15 октября 2023 18:00 Ужин",
        parse_mode="Markdown"
    )

@dp.message(lambda message: len(message.text.split()) >= 2 and not message.text.startswith('/'))
async def process_add_event(message: Message):
    try:
        logger.info(f"User {message.from_user.id} написал событие: {message.text}")
        date_part, event = message.text.split(maxsplit=1)
        event = event.strip()
        
        if not event:
            logger.warning(f"User {message.from_user.id} пытался добавить пустое событие")
            return await message.answer(
                "❌ Событие не может быть пустым.",
                reply_markup=get_main_keyboard()
            )


        parsed_date = parser.parse(date_part, dayfirst=True, fuzzy=False)
        

        if not parsed_date.tzinfo:
            parsed_date = MOSCOW_TZ.localize(parsed_date)
        date = parsed_date.strftime('%d-%m-%Y %H:%M')
        cursor.execute(
            'INSERT INTO events (date, event) VALUES (?, ?)', 
            (date, event)
        )
        conn.commit()
        
        logger.success(f"Событие добавлено пользователем {message.from_user.id}: {date} - {event}")
        await message.answer(
            f"✅ Событие добавлено!\n\n"
            f"📅 Дата: {date}\n"
            f"📝 Событие: {event}",
            reply_markup=get_main_keyboard()
        )
        
    except ValueError:
        logger.error(f"Неверный формат даты от пользователя {message.from_user.id}: {message.text}")
        await message.answer(
            "❌ Неверный формат даты. Используйте ДД-ММ-ГГГГ [ЧЧ:ММ]\n"
            "Примеры:\n"
            "• 15-10-2023 14:30 Встреча\n"
            "• 15.10.2023 День рождения\n"
            "• 15 октября 2023 18:00 Ужин",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.critical(f"Ошибка БД у пользователя {message.from_user.id}: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при добавлении",
            reply_markup=get_main_keyboard()
        )

@dp.message(lambda message: message.text == "📋 Показать события")
async def show_events_button(message: Message):
    logger.info(f"User {message.from_user.id} хочет посмотреть даты'")
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
    logger.info(f"User {message.from_user.id} хочет удалить дату (звчем?)'")
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
    logger.info(f"User {message.from_user.id} ищит дату'")
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

if __name__ == '__main__':
    logger.info("Starting bot...")
    executor.start_polling(dp, skip_updates=True)
