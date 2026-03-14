"""Referral system: /referral command and bonus spread usage."""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    get_user,
    generate_and_save_referral_code,
    count_referrals,
    use_referral_bonus,
)
from keyboards.menus import back_to_main, cancel_input
from texts.messages import ASK_QUESTION

router = Router()
logger = logging.getLogger(__name__)


# ─── /referral command ────────────────────────────────────────────────────────

@router.message(Command("referral"))
async def cmd_referral(message: Message):
    await _send_referral_card(message.from_user.id, message, edit=False)


@router.callback_query(F.data.in_({"menu:referral", "referral"}))
async def cb_referral(callback: CallbackQuery):
    await _send_referral_card(callback.from_user.id, callback.message, edit=True)
    await callback.answer()


# ─── Internal helper ──────────────────────────────────────────────────────────

async def _send_referral_card(uid: int, msg: Message, edit: bool = False):
    user      = await get_user(uid)
    code      = await generate_and_save_referral_code(uid)
    ref_count = await count_referrals(uid)
    bonuses   = (user or {}).get("referral_bonuses_available") or 0

    # How many more referrals until next bonus
    remainder = ref_count % 3
    next_bonus_in = (3 - remainder) if remainder != 0 else 3

    bot_info = await msg.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"

    text = (
        f"👥 *Приглашай друзей — получай бесплатные расклады*\n\n"
        f"🎁 *За каждых 3 приглашённых → 1 бесплатный Глубокий расклад*\n\n"
        f"Поделись ссылкой:\n\n"
        f"`{link}`\n\n"
        f"📊 *Твоя статистика:*\n"
        f"• Приглашено душ: *{ref_count}*\n"
        f"• Доступно бонусных раскладов: *{bonuses}*\n"
        f"• До следующего бонуса: ещё *{next_bonus_in}*\n"
    )

    if bonuses > 0:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🎁 Использовать бонус ({bonuses} шт.)", callback_data="referral:use_bonus")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ])
    else:
        markup = back_to_main()

    if edit:
        await msg.edit_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await msg.answer(text, reply_markup=markup, parse_mode="Markdown")


# ─── /use_bonus — activate bonus spread ──────────────────────────────────────

@router.message(Command("use_bonus"))
async def cmd_use_bonus(message: Message):
    await _activate_bonus(message.from_user.id, message, edit=False)


@router.callback_query(F.data == "referral:use_bonus")
async def cb_use_bonus(callback: CallbackQuery):
    await _activate_bonus(callback.from_user.id, callback.message, edit=True)
    await callback.answer()


async def _activate_bonus(uid: int, msg: Message, edit: bool = False):
    consumed = await use_referral_bonus(uid)
    if not consumed:
        text = (
            "🌌 У тебя пока нет бонусных раскладов.\n\n"
            "Приглашай друзей — за каждых 3 получай один бесплатный глубокий расклад!"
        )
        if edit:
            await msg.edit_text(text, reply_markup=back_to_main())
        else:
            await msg.answer(text, reply_markup=back_to_main())
        return

    text = (
        "✨ *Бонусный расклад активирован!*\n\n"
        "Звёзды открывают для тебя особый канал...\n"
        "Выбери расклад в главном меню — он будет бесплатным."
    )
    if edit:
        await msg.edit_text(text, reply_markup=back_to_main(), parse_mode="Markdown")
    else:
        await msg.answer(text, reply_markup=back_to_main(), parse_mode="Markdown")
