from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import config
from database import (
    get_stats,
    get_user,
    save_spread,
    create_journey,
    advance_journey,
    get_recent_spreads,
)
from keyboards.menus import reaction_keyboard
from services import oracle
from services.context import build_system_prompt
from services.limiter import ensure_user
from texts.messages import (
    ADMIN_STATS_TEMPLATE,
    NOT_ADMIN,
    PAYMENT_SUCCESS_JOURNEY,
    SPREAD_JOURNEY_DAY_INTRO,
)

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != config.admin_id:
        await message.answer(NOT_ADMIN)
        return

    stats = await get_stats()
    text = ADMIN_STATS_TEMPLATE.format(**stats)
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("test"))
async def cmd_test(message: Message, state: FSMContext):
    if message.from_user.id != config.admin_id:
        await message.answer(NOT_ADMIN)
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "Использование: /test <product>\n"
            "Продукты: mirror, year, compat, ritual, journey"
        )
        return

    product = parts[1].lower()
    uid = message.from_user.id
    await ensure_user(uid, message.from_user.username)

    from handlers.spreads import SpreadState

    if product == "mirror":
        await state.set_state(SpreadState.waiting_question_mirror)
        await message.answer("🧪 [TEST] Глубокий расклад. Задай вопрос:")

    elif product == "year":
        await state.set_state(SpreadState.waiting_question_year)
        await message.answer("🧪 [TEST] Год под звёздами. Задай вопрос:")

    elif product == "compat":
        await state.set_state(SpreadState.waiting_question_compat)
        await message.answer("🧪 [TEST] Совместимость. Задай вопрос:")

    elif product == "ritual":
        await state.set_state(SpreadState.waiting_question_ritual)
        await message.answer("🧪 [TEST] Лунный ритуал. Задай вопрос:")

    elif product == "journey":
        await message.answer(PAYMENT_SUCCESS_JOURNEY)
        journey_id = await create_journey(uid)
        user = await get_user(uid)
        recent = await get_recent_spreads(uid, limit=3)
        system_prompt = build_system_prompt(user or {}, recent)
        try:
            text = await oracle.generate_journey_day(1, system_prompt)
            spread_id = await save_spread(uid, "journey_1", "День 1: Твоя текущая энергия", text, None)
            intro = SPREAD_JOURNEY_DAY_INTRO.format(day=1)
            await message.answer(intro + text, reply_markup=reaction_keyboard(spread_id), parse_mode="Markdown")
        except Exception as e:
            await message.answer(f"❌ Ошибка генерации: {e}")
        await advance_journey(journey_id)

    else:
        await message.answer(
            f"Неизвестный продукт: {product}\n"
            "Продукты: mirror, year, compat, ritual, journey"
        )
