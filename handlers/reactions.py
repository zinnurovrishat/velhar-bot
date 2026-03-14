"""Reaction buttons shown after each spread result."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import get_spread_by_id
from keyboards.menus import main_menu

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("react:me_"))
async def react_me(callback: CallbackQuery):
    """User confirms the reading resonates — just a toast, no state change."""
    await callback.answer("🌌 Звёзды слышат тебя...", show_alert=False)


@router.callback_query(F.data == "react:more")
async def react_more(callback: CallbackQuery):
    """User wants another question — show main menu."""
    await callback.answer()  # answer first
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        "✨ Звёзды готовы открыть новое послание.\nЧто тревожит твою душу?",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data.startswith("react:share_"))
async def react_share(callback: CallbackQuery):
    """Prepare a shareable text card from the spread."""
    # Answer immediately — prevents Telegram loading spinner from hanging
    await callback.answer()

    try:
        spread_id = int(callback.data.split("_", 1)[1])
    except (ValueError, IndexError):
        await callback.message.answer("❌ Не удалось загрузить расклад")
        return

    spread = await get_spread_by_id(spread_id)
    if not spread:
        await callback.message.answer("❌ Расклад не найден")
        return

    response_text = spread.get("response", "")
    preview = response_text[:700].rstrip()
    if len(response_text) > 700:
        preview += "..."

    bot_info = await callback.bot.get_me()
    share_text = (
        f"🌌 Послание VELHAR\n\n"
        f"{preview}\n\n"
        f"Получи своё послание: @{bot_info.username}"
    )

    await callback.message.answer(share_text, parse_mode=None)
