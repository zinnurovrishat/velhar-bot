"""
Intent handler — catches free-text messages when no FSM state is active.
Handles who/real/ai/doubt/need_help/future/thanks intents
and Velhar's 'cold' state logic.
"""
import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import Message

from database import (
    get_user,
    get_recent_spreads,
    increment_ai_question_count,
    set_velhar_state,
    reset_velhar_state,
    update_last_active,
)
from keyboards.menus import main_menu, back_to_main
from services.intent_detector import detect_intent
from services.oracle import _ask_velhar
from services.context import build_system_prompt
from services.utils import velhar_typing
from texts.velhar_voice import (
    INTENT_WHO,
    INTENT_REAL,
    INTENT_AI_SOFT,
    INTENT_AI_HARD,
    INTENT_AI_COLD,
    INTENT_DOUBT,
    INTENT_HELP,
    INTENT_FUTURE,
    INTENT_THANKS,
    STATE_COLD_DEFAULT,
    UNKNOWN_MESSAGE,
)

router = Router()
logger = logging.getLogger(__name__)

# FSM state for emotional support conversation
class SupportState(StatesGroup):
    listening = State()


# ─── Main free-text handler ───────────────────────────────────────────────────

@router.message(StateFilter(default_state), F.text)
async def handle_free_text(message: Message, state: FSMContext):
    text = message.text or ""
    intent = detect_intent(text)
    uid = message.from_user.id

    await update_last_active(uid)
    user = await get_user(uid)
    velhar_state = (user or {}).get("velhar_state") or "calm"

    # ── Cold state: only trolling intents get the cold response ──────────────
    if velhar_state == "cold":
        if intent in ("who_are_you", "are_you_real", "are_you_ai", "doubt", "future"):
            await velhar_typing(message.bot, message.chat.id, long=False)
            await message.answer(STATE_COLD_DEFAULT)
            return
        elif intent is None:
            # Real question — reset cold state, show menu
            await reset_velhar_state(uid)
            await velhar_typing(message.bot, message.chat.id, long=False)
            await message.answer(
                "Велхар слышит тебя.\n\nВыбери расклад:",
                reply_markup=main_menu(),
            )
            return
        # thanks / need_help in cold state — handle normally below

    # ── Intent dispatch ───────────────────────────────────────────────────────
    if intent == "who_are_you":
        await velhar_typing(message.bot, message.chat.id, long=False)
        await message.answer(INTENT_WHO)

    elif intent == "are_you_real":
        await velhar_typing(message.bot, message.chat.id, long=False)
        await message.answer(INTENT_REAL)

    elif intent == "are_you_ai":
        await velhar_typing(message.bot, message.chat.id, long=False)
        count = await increment_ai_question_count(uid)
        if count <= 2:
            await message.answer(INTENT_AI_SOFT)
        elif count == 3:
            await set_velhar_state(uid, "cold")
            await message.answer(INTENT_AI_HARD)
        else:
            await message.answer(INTENT_AI_COLD)

    elif intent == "doubt":
        await velhar_typing(message.bot, message.chat.id, long=False)
        await message.answer(INTENT_DOUBT)

    elif intent == "need_help":
        await velhar_typing(message.bot, message.chat.id, long=False)
        await state.set_state(SupportState.listening)
        await message.answer(INTENT_HELP)

    elif intent == "future":
        await velhar_typing(message.bot, message.chat.id, long=False)
        await message.answer(INTENT_FUTURE, reply_markup=main_menu())

    elif intent == "thanks":
        await velhar_typing(message.bot, message.chat.id, long=False)
        await message.answer(INTENT_THANKS)

    else:
        # No recognized intent — gently show the menu
        await velhar_typing(message.bot, message.chat.id, long=False)
        await message.answer(UNKNOWN_MESSAGE, reply_markup=main_menu())


# ─── Emotional support: next message ─────────────────────────────────────────

@router.message(SupportState.listening, F.text)
async def handle_support_reply(message: Message, state: FSMContext):
    """User shared something — Velhar responds with warmth, no spread."""
    await state.clear()
    uid = message.from_user.id

    user = await get_user(uid)
    recent = await get_recent_spreads(uid, limit=3)
    system_prompt = build_system_prompt(user or {}, recent)

    support_addon = (
        "\n\nВАЖНО ДЛЯ ЭТОГО ОТВЕТА:\n"
        "Пользователю сейчас тяжело. Отвечай тепло, без расклада таро. "
        "Выслушай и поддержи. Не предлагай карты, если только пользователь не попросит сам. "
        "Напомни: ты не заменяешь живых людей, которые могут помочь."
    )

    await velhar_typing(message.bot, message.chat.id, long=True)
    try:
        response = await _ask_velhar(message.text, system_prompt + support_addon)
        await message.answer(response, reply_markup=back_to_main())
    except Exception:
        logger.exception("Support reply failed")
        await message.answer(
            "Велхар слышит тебя. Пространство сейчас зашумело...\n\n"
            "Вернись немного позже.",
            reply_markup=back_to_main(),
        )
