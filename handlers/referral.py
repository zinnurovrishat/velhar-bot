"""Referral system: /referral command and bonus spread usage."""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

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


@router.callback_query(F.data == "menu:referral")
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

    bonus_line = (
        f"🎁 *У тебя есть {bonuses} бонусный расклад!*\n"
        f"Нажми /use\\_bonus чтобы использовать его.\n\n"
        if bonuses > 0 else ""
    )

    text = (
        f"👥 *Твой портал для друзей*\n\n"
        f"Поделись ссылкой — и новые души откроют путь к звёздам:\n\n"
        f"`{link}`\n\n"
        f"{bonus_line}"
        f"📊 *Статистика:*\n"
        f"• Приглашено душ: *{ref_count}*\n"
        f"• Бонусных раскладов: *{bonuses}*\n"
        f"• До следующего бонуса: ещё *{next_bonus_in}* чел.\n\n"
        f"_За каждых 3 приглашённых ты получаешь один бесплатный глубокий расклад_"
    )

    if edit:
        await msg.edit_text(text, reply_markup=back_to_main(), parse_mode="Markdown")
    else:
        await msg.answer(text, reply_markup=back_to_main(), parse_mode="Markdown")


# ─── /use_bonus — activate bonus spread ──────────────────────────────────────

@router.message(Command("use_bonus"))
async def cmd_use_bonus(message: Message):
    uid = message.from_user.id
    consumed = await use_referral_bonus(uid)
    if not consumed:
        await message.answer(
            "🌌 У тебя пока нет бонусных раскладов.\n\n"
            "Приглашай друзей — за каждых 3 получай один бесплатный расклад!\n"
            "/referral — твоя реферальная ссылка",
        )
        return

    await message.answer(
        "✨ *Бонусный расклад активирован!*\n\n"
        "Звёзды открывают для тебя особый канал...\n"
        "Выбери расклад в главном меню — он будет бесплатным.",
        reply_markup=back_to_main(),
        parse_mode="Markdown",
    )
