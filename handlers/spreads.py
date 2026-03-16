import asyncio
import logging
import random
from aiogram import Router, F

logger = logging.getLogger(__name__)
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
    increment_spreads_since_memory,
    reset_spreads_since_memory,
    update_streak,
)
from keyboards.menus import (
    back_to_main,
    cancel_input,
    limit_reached_menu,
    subscription_menu,
    reaction_keyboard,
    upsell_deep_reading,
    upsell_journey,
)
from services import oracle
from services.oracle import CARD_IMAGES
from services.context import build_system_prompt, get_moon_phase_text, get_time_of_day
from services.memory import should_use_memory, MEMORY_ADDON
from services.utils import velhar_typing
from services.limiter import (
    ensure_user,
    can_use_card_of_day,
    can_use_three_paths,
    can_use_month_spread,
    can_use_ritual,
    is_user_subscribed,
)
from services.moon import is_near_fullmoon, hours_in_fullmoon_window
from texts.messages import (
    ASK_QUESTION,
    ASK_QUESTION_COMPAT,
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
from texts.velhar_voice import LIMIT_REACHED, get_loading, get_rare_card_prefix, get_collective_mysticism, get_card_draw_animation, get_upsell_tease, get_rare_card_upsell_tease

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


# ─── Core helper ──────────────────────────────────────────────────────────────

async def _generate_and_send(
    msg_placeholder: Message,
    intro: str,
    generator_fn,
    question: str,
    user_id: int,
    spread_type: str,
    counter_fn=None,
) -> bool:
    """Build context, optionally inject memory, call oracle, save, show reactions.
    Returns True if a rare card moment was triggered."""
    draw_msg: Message | None = None
    try:
        await msg_placeholder.bot.send_chat_action(msg_placeholder.chat.id, "typing")

        user   = await get_user(user_id)
        recent = await get_recent_spreads(user_id, limit=5)

        system_prompt = build_system_prompt(user or {}, recent[:3])

        # Memory illusion — inject MEMORY_ADDON when recurring topic detected
        if should_use_memory(user or {}, question, recent):
            system_prompt += MEMORY_ADDON
            await reset_spreads_since_memory(user_id)
        else:
            await increment_spreads_since_memory(user_id)

        result = await generator_fn(question, system_prompt=system_prompt)
        drawn_cards, text = result if isinstance(result, tuple) else ([], result)

        try:
            summary = await oracle.generate_summary(text)
        except Exception:
            summary = None

        spread_id = await save_spread(user_id, spread_type, question, text, summary)
        await update_last_active(user_id)

        # Rare card moment — 4% probability
        rare_triggered = random.random() < 0.04
        rare_prefix = get_rare_card_prefix() if rare_triggered else ""

        # Collective mysticism — 10% probability
        collective_prefix = get_collective_mysticism() if random.random() < 0.10 else ""

        full_output = rare_prefix + collective_prefix + intro + text

        # Send card images (Major Arcana only, max 3)
        card_imgs = [CARD_IMAGES[c] for c in drawn_cards if c in CARD_IMAGES][:3]

        await msg_placeholder.delete()

        if len(card_imgs) == 1:
            await msg_placeholder.bot.send_photo(
                msg_placeholder.chat.id,
                photo=card_imgs[0],
                disable_notification=True,
            )
        elif len(card_imgs) > 1:
            from aiogram.types import InputMediaPhoto
            media = [InputMediaPhoto(media=url) for url in card_imgs]
            await msg_placeholder.bot.send_media_group(
                msg_placeholder.chat.id,
                media=media,
                disable_notification=True,
            )

        draw_msg = await msg_placeholder.bot.send_message(
            msg_placeholder.chat.id,
            get_card_draw_animation(),
        )
        await asyncio.sleep(2)

        try:
            await draw_msg.edit_text(
                full_output,
                reply_markup=reaction_keyboard(spread_id),
                parse_mode="Markdown",
            )
        except Exception:
            await draw_msg.edit_text(
                full_output,
                reply_markup=reaction_keyboard(spread_id),
            )

        if counter_fn:
            await counter_fn(user_id)

        # Streak tracking
        streak, is_milestone = await update_streak(user_id)
        if is_milestone:
            from texts.messages import STREAK_MILESTONES
            milestone_text = STREAK_MILESTONES.get(streak)
            if milestone_text:
                await asyncio.sleep(3)
                await draw_msg.bot.send_message(
                    draw_msg.chat.id, milestone_text, parse_mode="Markdown"
                )

        return rare_triggered

    except Exception as e:
        logger.exception("_generate_and_send failed (user=%s spread=%s): %s", user_id, spread_type, e)
        error_target = draw_msg if draw_msg is not None else msg_placeholder
        try:
            await error_target.edit_text(ERROR_GENERIC, reply_markup=back_to_main())
        except Exception:
            try:
                await msg_placeholder.bot.send_message(
                    msg_placeholder.chat.id, ERROR_GENERIC, reply_markup=back_to_main()
                )
            except Exception:
                pass
    return False


def _loading(spread_type: str) -> str:
    return get_loading(spread_type, get_moon_phase_text(), get_time_of_day())


# ─── Card of day  (spread_day / spread:card_of_day) ───────────────────────────

@router.callback_query(F.data.in_({"spread_day", "spread:card_of_day"}))
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
    placeholder = await message.answer(_loading("spread_day"))
    await velhar_typing(message.bot, message.chat.id, long=True)
    rare = await _generate_and_send(
        placeholder, SPREAD_CARD_OF_DAY_INTRO,
        oracle.generate_card_of_day, message.text,
        user_id=uid, spread_type="spread_day", counter_fn=increment_free_used,
    )
    if rare:
        await _maybe_rare_upsell(message)
    else:
        await _maybe_upsell(message, uid)


# ─── Three paths / Задать вопрос  (spread_question / spread:three_paths) ──────

@router.callback_query(F.data.in_({"spread_question", "spread:three_paths"}))
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
    placeholder = await message.answer(_loading("spread_question"))
    await velhar_typing(message.bot, message.chat.id, long=True)
    rare = await _generate_and_send(
        placeholder, SPREAD_THREE_PATHS_INTRO,
        oracle.generate_three_paths, message.text,
        user_id=uid, spread_type="spread_question", counter_fn=increment_free_used,
    )
    if rare:
        await _maybe_rare_upsell(message)
    else:
        await _maybe_upsell(message, uid)


# ─── Deep spread / Глубокий расклад  (spread_deep / spread:mirror) ────────────

@router.callback_query(F.data.in_({"spread_deep", "spread:mirror"}))
async def cb_mirror(callback: CallbackQuery, state: FSMContext):
    from handlers.payment import _start_payment
    await _start_payment(callback, "mirror")


@router.message(SpreadState.waiting_question_mirror)
async def msg_mirror(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    placeholder = await message.answer(_loading("spread_deep"))
    await velhar_typing(message.bot, message.chat.id, long=True)
    await _generate_and_send(
        placeholder, SPREAD_MIRROR_INTRO,
        oracle.generate_mirror_of_fate, message.text,
        user_id=uid, spread_type="spread_deep", counter_fn=increment_paid_mirror,
    )


# ─── Year under stars  (spread:year) ──────────────────────────────────────────

@router.callback_query(F.data == "spread:year")
async def cb_year(callback: CallbackQuery, state: FSMContext):
    from handlers.payment import _start_payment
    await _start_payment(callback, "spread_year")


@router.message(SpreadState.waiting_question_year)
async def msg_year(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    placeholder = await message.answer(_loading("spread_year"))
    await velhar_typing(message.bot, message.chat.id, long=True)
    await _generate_and_send(
        placeholder, SPREAD_YEAR_INTRO,
        oracle.generate_year_under_stars, message.text,
        user_id=uid, spread_type="spread_year", counter_fn=increment_paid_year,
    )


# ─── Ritual  (ritual / spread:ritual) ─────────────────────────────────────────

@router.callback_query(F.data.in_({"ritual", "spread:ritual"}))
async def cb_ritual(callback: CallbackQuery, state: FSMContext):
    if not is_near_fullmoon():
        from services.context import get_days_until_fullmoon
        days_left = get_days_until_fullmoon()
        await callback.message.edit_text(
            NOT_FULLMOON + f"\n\n_Следующее полнолуние — примерно через {days_left} дней._",
            reply_markup=back_to_main(), parse_mode="Markdown"
        )
        await callback.answer()
        return
    hours = hours_in_fullmoon_window()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from config import PRICES_STARS
    fomo_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"🌕 Открыть лунные врата — {PRICES_STARS['ritual']} ⭐", callback_data="ritual:confirm"),
        ], [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
    ])
    await callback.message.edit_text(
        f"🌕 *Лунные врата открыты.*\n\n"
        f"Полнолуние наступило.\n"
        f"Этот расклад раскрывает то, что скрыто под поверхностью текущего цикла.\n\n"
        f"⏳ *Доступно ещё примерно {hours} часов.*\n\n"
        f"Семь карт. Послание из глубин.",
        reply_markup=fomo_markup,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "ritual:confirm")
async def cb_ritual_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_near_fullmoon():
        await callback.answer("Окно закрылось.", show_alert=True)
        return
    from handlers.payment import _start_payment
    await _start_payment(callback, "ritual")


# ─── Journey  (spread:journey / menu:journey) ─────────────────────────────────

@router.callback_query(F.data == "menu:journey")
async def cb_journey_intro(callback: CallbackQuery, state: FSMContext):
    """Показывает вводный экран 7-дневного пути перед оплатой."""
    from keyboards.menus import journey_intro_menu
    await callback.message.edit_text(
        "🌟 *Путь озарения — 7 дней*\n\n"
        "В течение семи дней Велхар будет тянуть для тебя одну карту каждое утро.\n"
        "Каждый день несёт свою тему — другой взгляд на себя.\n\n"
        "📌 *Семь тем:*\n"
        "День 1 — Твоя текущая энергия\n"
        "День 2 — Скрытые влияния\n"
        "День 3 — Предстоящее испытание\n"
        "День 4 — Твоя внутренняя сила\n"
        "День 5 — Точка перелома\n"
        "День 6 — Что нужно отпустить\n"
        "День 7 — Путь вперёд\n\n"
        "День 1 приходит сразу после начала.\n"
        "Дни 2–7 — каждое утро в 13:00 по МСК.",
        reply_markup=journey_intro_menu(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "spread:journey")
async def cb_journey(callback: CallbackQuery, state: FSMContext):
    from handlers.payment import _start_payment
    await _start_payment(callback, "journey")


@router.message(SpreadState.waiting_question_ritual)
async def msg_ritual(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    placeholder = await message.answer(_loading("ritual"))
    await velhar_typing(message.bot, message.chat.id, long=True)
    await _generate_and_send(
        placeholder, SPREAD_RITUAL_INTRO,
        oracle.generate_fullmoon_ritual, message.text,
        user_id=uid, spread_type="ritual", counter_fn=increment_total_spreads,
    )


# ─── Compatibility  (spread:compat) ───────────────────────────────────────────

@router.callback_query(F.data == "spread:compat")
async def cb_compat(callback: CallbackQuery, state: FSMContext):
    from handlers.payment import _start_payment
    await _start_payment(callback, "spread_compat")


@router.message(SpreadState.waiting_question_compat)
async def msg_compat(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    placeholder = await message.answer(_loading("spread_compat"))
    await velhar_typing(message.bot, message.chat.id, long=True)
    await _generate_and_send(
        placeholder, SPREAD_COMPAT_INTRO,
        oracle.generate_compatibility, message.text,
        user_id=uid, spread_type="spread_compat", counter_fn=increment_total_spreads,
    )


# ─── Month spread  (subscription) ─────────────────────────────────────────────

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
    placeholder = await message.answer(_loading("month_spread"))
    await velhar_typing(message.bot, message.chat.id, long=True)
    await _generate_and_send(
        placeholder, SPREAD_MONTH_INTRO,
        oracle.generate_subscription_spread, message.text,
        user_id=uid, spread_type="month_spread", counter_fn=increment_total_spreads,
    )


# ─── Post-spread upsell ───────────────────────────────────────────────────────

async def _maybe_upsell(message: Message, uid: int):
    """После бесплатного расклада намекает на платный (80% шанс).
    Первые 3 расклада → Journey; далее → Mirror of Fate."""
    db_user = await get_user(uid)
    if not db_user or not db_user.get("name"):
        return
    total = db_user.get("total_spreads", 0) or 0
    if total < 1:
        return
    if random.random() > 0.80:
        return
    await asyncio.sleep(4)
    if total < 3:
        await message.answer(
            "Шёпот услышан... 🌌\n\n"
            "Хочешь идти глубже? *7 дней, 7 карт* — персональный путь под руководством Велхара.\n"
            "Каждое утро новая карта и тема. Начало — сразу после старта.",
            reply_markup=upsell_journey(),
            parse_mode="Markdown",
        )
    else:
        await message.answer(get_upsell_tease(), reply_markup=upsell_deep_reading(), parse_mode="Markdown")


async def _maybe_rare_upsell(message: Message):
    """После редкой карты — всегда показывает апселл."""
    await asyncio.sleep(3)
    await message.answer(get_rare_card_upsell_tease(), reply_markup=upsell_deep_reading(), parse_mode="Markdown")
