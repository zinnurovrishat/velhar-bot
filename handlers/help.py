"""Handler for /help command — support contact."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

_SUPPORT_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="✉️ Написать в поддержку", url="https://t.me/zinnurovrishat"),
]])

HELP_TEXT = (
    "🔮 *Велхар всегда здесь.*\n\n"
    "Если что-то пошло не так или есть вопрос — напиши напрямую создателю.\n\n"
    "Обычно отвечаю в течение дня."
)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, reply_markup=_SUPPORT_KB)
