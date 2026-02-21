from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from database import get_user
from keyboards.menus import main_menu, subscription_menu
from services.limiter import ensure_user, is_user_subscribed
from texts.messages import WELCOME, WELCOME_BACK, SUBSCRIPTION_INFO

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    await ensure_user(user.id, user.username)

    existing = await get_user(user.id)
    # If user was created just now total_spreads == 0 → greet fresh
    is_new = existing is None or existing.get("total_spreads", 0) == 0

    text = WELCOME if is_new else WELCOME_BACK
    await message.answer(text, reply_markup=main_menu(), parse_mode="Markdown")


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        WELCOME_BACK, reply_markup=main_menu(), parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "menu:subscription")
async def cb_subscription_menu(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    subscribed = is_user_subscribed(user) if user else False

    status_line = ""
    if subscribed:
        until = user.get("subscription_until", "")
        if until:
            status_line = f"\n\n_Твоя подписка активна до: {str(until)[:10]}_"

    await callback.message.edit_text(
        SUBSCRIPTION_INFO + status_line,
        reply_markup=subscription_menu(is_subscribed=subscribed),
        parse_mode="Markdown",
    )
    await callback.answer()
