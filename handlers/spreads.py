import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    get_user,
    update_last_active,
    increment_free_used,
    increment_total_spreads,
    increment_paid_mirror,
    increment_paid_year,
    get_recent_spreads,
    save_spread,
)
from keyboards.menus import (
    back_to_main,
    cancel_input,
    limit_reached_menu,
    subscription_menu,
    reaction_keyboard,
)
from services import oracle
from services.context import build_system_prompt
from services.limiter import (
    ensure_user,
    can_use_card_of_day,
    can_use_three_paths,
    can_use_month_spread,
    can_use_ritual,
    is_user_subscribed,
)
from services.moon import is_near_fullmoon
from texts.messages import (
    ASK_QUESTION,
    ASK_QUESTION_COMPAT,
    THINKING,
    LIMIT_REACHED,
    NOT_FULLMOON,
    ERROR_GENERIC,
    SPREAD_CARD_OF_DAY_INTRO,
    SPREAD_THREE_PATHS_INTRO,
    SPREAD_MIRROR_INTRO,
    SPREAD_YEAR_INTRO,
    SPREAD_RITUAL_INTRO,
    SPREAD_MONTH_INTRO,
    SPREAD_COMPAT_INTRO,
)

router = Router()

# ─── FSM States ───────────────────────────────────────────────────────────────

class SpreadState(StatesGroup):
    waiting_question_card   = State()
    waiting_question_three  = State()
    waiting_question_mirror = State()
    waiting_question_year   = State()
    waiting_question_ritual = State()
    waiting_question_month  = State()
    waiting_question_compat = State()


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _generate_and_send(
    msg_placeholder: Message,
    intro: str,
    generator_fn,
    question: str,
    user_id: int,
    spread_type: str,
    counter_fn=None,
):
    """Run oracle with personalised context, save spread, show reaction keyboard."""
    try:
        await msg_placeholder.bot.send_chat_action(msg_placeholder.chat.id, "typing")

        # Build personalised system prompt
        user          = await get_user(user_id)
        recent        = await get_recent_spreads(user_id, limit=3)
        system_prompt = build_system_prompt(user or {}, recent)

        text = await generator_fn(question, system_prompt=system_prompt)

        # Generate 1-sentence summary for memory
        try:
            summary = await oracle.generate_summary(text)
        except Exception:
            summary = None

        # Persist spread
        spread_id = await save_spread(user_id, spread_type, question, text, summary)
        await update_last_active(user_id)

        await msg_placeholder.delete()
        await msg_placeholder.bot.send_message(
            msg_placeholder.chat.id,
            intro + text,
            reply_markup=reaction_keyboard(spread_id),
            parse_mode="Markdown",
        )

        if counter_fn:
            await counter_fn(user_id)

    except Exception:
        await msg_placeholder.edit_text(ERROR_GENERIC, reply_markup=back_to_main())


# ─── Card of day ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "spread:card_of_day")
async def cb_card_of_day(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await ensure_user(uid, callback.from_user.username)
    allowed, _ = await can_use_card_of_day(uid)
    if not allowed:
        await callback.message.edit_text(LIMIT_REACHED, reply_markup=limit_reached_menu())
        await callback.answer()
        return
    await state.set_state(SpreadState.waiting_question_card)
    await callback.message.edit_text(ASK_QUESTION, reply_markup=cancel_input(), parse_mode="Markdown")
    await callback.answer()


@router.message(SpreadState.waiting_question_card)
async def msg_card_of_day(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    allowed, _ = await can_use_card_of_day(uid)
    if not allowed:
        await message.answer(LIMIT_REACHED, reply_markup=limit_reached_menu())
        return
    placeholder = await message.answer(THINKING)
    await message.bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(2)
    await _generate_and_send(
        placeholder,
        SPREAD_CARD_OF_DAY_INTRO,
        oracle.generate_card_of_day,
        message.text,
        user_id=uid,
        spread_type="card_of_day",
        counter_fn=increment_free_used,
    )


# ─── Three paths ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "spread:three_paths")
async def cb_three_paths(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await ensure_user(uid, callback.from_user.username)
    allowed, _ = await can_use_three_paths(uid)
    if not allowed:
        await callback.message.edit_text(LIMIT_REACHED, reply_markup=limit_reached_menu())
        await callback.answer()
        return
    await state.set_state(SpreadState.waiting_question_three)
    await callback.message.edit_text(ASK_QUESTION, reply_markup=cancel_input(), parse_mode="Markdown")
    await callback.answer()


@router.message(SpreadState.waiting_question_three)
async def msg_three_paths(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    allowed, _ = await can_use_three_paths(uid)
    if not allowed:
        await message.answer(LIMIT_REACHED, reply_markup=limit_reached_menu())
        return
    placeholder = await message.answer(THINKING)
    await message.bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(2)
    await _generate_and_send(
        placeholder,
        SPREAD_THREE_PATHS_INTRO,
        oracle.generate_three_paths,
        message.text,
        user_id=uid,
        spread_type="three_paths",
        counter_fn=increment_free_used,
    )


# ─── Mirror of fate (paid) ────────────────────────────────────────────────────

@router.callback_query(F.data == "spread:mirror")
async def cb_mirror(callback: CallbackQuery, state: FSMContext):
    from handlers.payment import _start_payment
    await _start_payment(callback, "mirror")


@router.message(SpreadState.waiting_question_mirror)
async def msg_mirror(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    placeholder = await message.answer(THINKING)
    await message.bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(3)
    await _generate_and_send(
        placeholder,
        SPREAD_MIRROR_INTRO,
        oracle.generate_mirror_of_fate,
        message.text,
        user_id=uid,
        spread_type="mirror",
        counter_fn=increment_paid_mirror,
    )


# ─── Year under stars (paid) ──────────────────────────────────────────────────

@router.callback_query(F.data == "spread:year")
async def cb_year(callback: CallbackQuery, state: FSMContext):
    from handlers.payment import _start_payment
    await _start_payment(callback, "spread_year")


@router.message(SpreadState.waiting_question_year)
async def msg_year(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    placeholder = await message.answer(THINKING)
    await message.bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(3)
    await _generate_and_send(
        placeholder,
        SPREAD_YEAR_INTRO,
        oracle.generate_year_under_stars,
        message.text,
        user_id=uid,
        spread_type="year_under_stars",
        counter_fn=increment_paid_year,
    )


# ─── Full-moon ritual (paid) ──────────────────────────────────────────────────

@router.callback_query(F.data == "spread:ritual")
async def cb_ritual(callback: CallbackQuery, state: FSMContext):
    if not is_near_fullmoon():
        await callback.message.edit_text(NOT_FULLMOON, reply_markup=back_to_main(), parse_mode="Markdown")
        await callback.answer()
        return
    from handlers.payment import _start_payment
    await _start_payment(callback, "ritual")


@router.message(SpreadState.waiting_question_ritual)
async def msg_ritual(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    placeholder = await message.answer(THINKING)
    await message.bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(3)
    await _generate_and_send(
        placeholder,
        SPREAD_RITUAL_INTRO,
        oracle.generate_fullmoon_ritual,
        message.text,
        user_id=uid,
        spread_type="ritual",
        counter_fn=increment_total_spreads,
    )


# ─── Compatibility spread (paid) ──────────────────────────────────────────────

@router.callback_query(F.data == "spread:compat")
async def cb_compat(callback: CallbackQuery, state: FSMContext):
    from handlers.payment import _start_payment
    await _start_payment(callback, "spread_compat")


@router.message(SpreadState.waiting_question_compat)
async def msg_compat(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    placeholder = await message.answer(THINKING)
    await message.bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(3)
    await _generate_and_send(
        placeholder,
        SPREAD_COMPAT_INTRO,
        oracle.generate_compatibility,
        message.text,
        user_id=uid,
        spread_type="compatibility",
        counter_fn=increment_total_spreads,
    )


# ─── Month spread (subscription) ──────────────────────────────────────────────

@router.callback_query(F.data == "spread:month")
async def cb_month_spread(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await ensure_user(uid, callback.from_user.username)
    allowed, _ = await can_use_month_spread(uid)
    if not allowed:
        user = await get_user(uid)
        await callback.message.edit_text(
            "Расклад на месяц вперёд доступен только подписчикам VELHAR...",
            reply_markup=subscription_menu(is_subscribed=is_user_subscribed(user) if user else False),
        )
        await callback.answer()
        return
    await state.set_state(SpreadState.waiting_question_month)
    await callback.message.edit_text(ASK_QUESTION, reply_markup=cancel_input(), parse_mode="Markdown")
    await callback.answer()


@router.message(SpreadState.waiting_question_month)
async def msg_month_spread(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    placeholder = await message.answer(THINKING)
    await message.bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(3)
    await _generate_and_send(
        placeholder,
        SPREAD_MONTH_INTRO,
        oracle.generate_subscription_spread,
        message.text,
        user_id=uid,
        spread_type="month_spread",
        counter_fn=increment_total_spreads,
    )
