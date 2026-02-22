from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    get_user,
    update_user_name,
    update_user_zodiac,
    update_last_active,
    generate_and_save_referral_code,
    find_user_by_referral_code,
    set_referred_by,
    count_referrals,
    add_referral_bonus,
)
from keyboards.menus import main_menu, subscription_menu, zodiac_keyboard
from services.limiter import ensure_user, is_user_subscribed
from texts.messages import WELCOME, WELCOME_BACK, SUBSCRIPTION_INFO

router = Router()


# ─── Onboarding FSM ───────────────────────────────────────────────────────────

class OnboardingState(StatesGroup):
    waiting_name   = State()
    waiting_zodiac = State()


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = message.from_user
    await ensure_user(user.id, user.username)
    await update_last_active(user.id)

    # Handle referral code: /start <REF_CODE>
    args = message.text.split(maxsplit=1)
    ref_code = args[1].strip() if len(args) > 1 else None
    if ref_code:
        referrer = await find_user_by_referral_code(ref_code)
        if referrer and referrer["user_id"] != user.id:
            await set_referred_by(user.id, referrer["user_id"])
            ref_count = await count_referrals(referrer["user_id"])
            # Award bonus for every 3rd referral
            if ref_count > 0 and ref_count % 3 == 0:
                await add_referral_bonus(referrer["user_id"])
                try:
                    await message.bot.send_message(
                        referrer["user_id"],
                        f"🎁 *Звёздный подарок!*\n\n"
                        f"К тебе пришёл новый путник по твоему зову. "
                        f"Ты привлёк уже *{ref_count}* душ — "
                        f"тебе открыт *один бесплатный глубокий расклад*!\n\n"
                        f"Используй его в разделе раскладов.",
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass

    db_user = await get_user(user.id)

    # If user has no name — start onboarding
    if not db_user or not db_user.get("name"):
        await state.set_state(OnboardingState.waiting_name)
        await message.answer(
            "✨ *Добро пожаловать в пространство VELHAR*\n\n"
            "Я — космический оракул, читающий нити судьбы "
            "в пространстве между измерениями...\n\n"
            "Прежде чем карты откроются тебе, скажи:\n"
            "*Как мне называть тебя, путник?*",
            parse_mode="Markdown",
        )
        return

    # Returning user — generate code if missing, show menu
    await generate_and_save_referral_code(user.id)
    is_new = db_user.get("total_spreads", 0) == 0
    text = WELCOME if is_new else WELCOME_BACK
    await message.answer(text, reply_markup=main_menu(), parse_mode="Markdown")


# ─── Onboarding: name input ───────────────────────────────────────────────────

@router.message(OnboardingState.waiting_name)
async def onboarding_name(message: Message, state: FSMContext):
    name = message.text.strip()[:50]
    await update_user_name(message.from_user.id, name)
    await state.set_state(OnboardingState.waiting_zodiac)
    await message.answer(
        f"✨ *{name}*... красивое имя для путника между мирами.\n\n"
        f"Под каким знаком зодиака ты явился в этот мир?",
        reply_markup=zodiac_keyboard(),
        parse_mode="Markdown",
    )


# ─── Onboarding: zodiac selection ─────────────────────────────────────────────

@router.callback_query(OnboardingState.waiting_zodiac, F.data.startswith("zodiac:"))
async def onboarding_zodiac(callback: CallbackQuery, state: FSMContext):
    zodiac = callback.data.split(":", 1)[1]
    uid = callback.from_user.id
    await update_user_zodiac(uid, zodiac)
    await state.clear()

    referral_code = await generate_and_save_referral_code(uid)
    db_user = await get_user(uid)
    name = db_user.get("name", "путник") if db_user else "путник"

    await callback.message.edit_text(
        f"🌌 *{zodiac}* — знак, несущий свою особую силу и свет...\n\n"
        f"Добро пожаловать, *{name}*. Звёзды ждали твоего прихода.\n\n"
        f"Что ведёт тебя сегодня?",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ─── Main menu callbacks ──────────────────────────────────────────────────────

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
