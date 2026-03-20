"""Reaction buttons shown after each spread result."""
import logging
import urllib.parse

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user, set_daily_notify
from keyboards.menus import main_menu, daily_notify_menu
from texts.messages import (
    DAILY_NOTIFY_MENU_ON,
    DAILY_NOTIFY_MENU_OFF,
    DAILY_NOTIFY_ON,
    DAILY_NOTIFY_OFF,
)

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("react:me_"))
async def react_me(callback: CallbackQuery):
    """User confirms the reading resonates — just a toast, no state change."""
    await callback.answer("🌌 Звёзды слышат тебя...", show_alert=False)


@router.callback_query(F.data == "react:more")
async def react_more(callback: CallbackQuery):
    """User wants another question — show main menu."""
    await callback.answer()
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
    """Generate a short poetic share card from the spread."""
    await callback.answer()

    # Use message text directly — no DB lookup needed, survives redeploys
    response_text = (callback.message.text or "").strip()

    from services import oracle
    try:
        short_text = await oracle.generate_share_card(response_text)
    except Exception:
        short_text = response_text[:200] if response_text else "Велхар видит тебя."

    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username

    share_message = (
        f"✨ Послание Велхара\n\n"
        f"{short_text}\n\n"
        f"Вытяни свою карту: @{bot_username}"
    )

    share_url = urllib.parse.quote(f"https://t.me/{bot_username}", safe="")
    quoted = urllib.parse.quote(short_text + f"\n\nВытяни свою карту: @{bot_username}")
    share_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📤 Переслать другу",
            url=f"https://t.me/share/url?url={share_url}&text={quoted}",
        )
    ]])

    try:
        await callback.message.answer(share_message, reply_markup=share_markup)
    except Exception:
        await callback.answer("❌ Не удалось создать карточку", show_alert=True)


# ─── Daily notify ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:daily_notify")
async def notify_daily_menu(callback: CallbackQuery):
    uid = callback.from_user.id
    user = await get_user(uid)
    enabled = bool(user.get("daily_notify")) if user else False
    text = DAILY_NOTIFY_MENU_ON if enabled else DAILY_NOTIFY_MENU_OFF
    await callback.message.edit_text(
        text, reply_markup=daily_notify_menu(enabled), parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.in_({"notify:daily_on", "notify:daily_off"}))
async def notify_daily_toggle(callback: CallbackQuery):
    uid = callback.from_user.id
    enabled = callback.data == "notify:daily_on"
    await set_daily_notify(uid, enabled)
    toast = DAILY_NOTIFY_ON if enabled else DAILY_NOTIFY_OFF
    text = DAILY_NOTIFY_MENU_ON if enabled else DAILY_NOTIFY_MENU_OFF
    await callback.answer(toast, show_alert=True)
    await callback.message.edit_text(
        text, reply_markup=daily_notify_menu(enabled), parse_mode="Markdown"
    )
