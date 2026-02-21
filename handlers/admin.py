from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import config
from database import get_stats
from texts.messages import ADMIN_STATS_TEMPLATE, NOT_ADMIN

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != config.admin_id:
        await message.answer(NOT_ADMIN)
        return

    stats = await get_stats()
    text = ADMIN_STATS_TEMPLATE.format(**stats)
    await message.answer(text, parse_mode="Markdown")
