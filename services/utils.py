"""Shared async utilities for VELHAR bot."""
import asyncio
from aiogram.enums import ChatAction


async def velhar_typing(bot, chat_id: int, long: bool = False):
    """Send typing action and wait a bit to simulate Velhar thinking."""
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(1.5 if long else 0.8)
