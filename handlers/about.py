"""Handler for /about command — three-part Velhar lore with pauses."""
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from services.utils import velhar_typing
from texts.velhar_voice import ABOUT_1, ABOUT_2, ABOUT_3

router = Router()

_QUESTION_BUTTON = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="🔮 Задать вопрос Велхару", callback_data="spread_question"),
]])


async def _send_about(bot, chat_id: int):
    await velhar_typing(bot, chat_id, long=True)
    await bot.send_message(chat_id, ABOUT_1)

    await asyncio.sleep(2.5)
    await velhar_typing(bot, chat_id, long=True)
    await bot.send_message(chat_id, ABOUT_2)

    await asyncio.sleep(2.5)
    await velhar_typing(bot, chat_id, long=True)
    await bot.send_message(chat_id, ABOUT_3, reply_markup=_QUESTION_BUTTON)


@router.message(Command("about"))
async def cmd_about(message: Message):
    await _send_about(message.bot, message.chat.id)


@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    await callback.answer()
    await _send_about(callback.bot, callback.message.chat.id)
