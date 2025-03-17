from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="📅 Добавить событие"))
    keyboard.add(KeyboardButton(text="📋 Показать события"))
    keyboard.add(KeyboardButton(text="❌ Удалить событие"))
    keyboard.add(KeyboardButton(text="🔍 События на дату"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)
