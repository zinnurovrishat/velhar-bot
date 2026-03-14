from datetime import datetime, timedelta, timezone

from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery,
    Message,
    LabeledPrice,
    PreCheckoutQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from config import config, PRICES_STARS, PRODUCT_TITLES, PRODUCT_DESCRIPTIONS
from database import set_subscription, create_payment, update_payment_status, create_journey, advance_journey, save_spread, get_user, get_recent_spreads
from keyboards.menus import back_to_main, reaction_keyboard
from texts.messages import (
    SUBSCRIPTION_ACTIVE,
    PAYMENT_SUCCESS_MIRROR,
    PAYMENT_SUCCESS_YEAR,
    PAYMENT_SUCCESS_RITUAL,
    PAYMENT_SUCCESS_COMPAT,
    PAYMENT_SUCCESS_JOURNEY,
    SPREAD_JOURNEY_DAY_INTRO,
)

router = Router()


# ─── Stars invoice keyboard (single Pay button) ───────────────────────────────

def _pay_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оплатить звёздами", pay=True)],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    )


# ─── Send invoice (called from spreads.py and subscription menu) ──────────────

async def _start_payment(callback: CallbackQuery, product_type: str):
    """Send a Telegram Stars invoice for the given product."""
    if product_type not in PRICES_STARS:
        await callback.answer("Неизвестный продукт", show_alert=True)
        return

    await callback.answer()

    await callback.message.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=PRODUCT_TITLES[product_type],
        description=PRODUCT_DESCRIPTIONS[product_type],
        payload=product_type,
        provider_token="",          # Empty string = Telegram Stars
        currency="XTR",
        prices=[
            LabeledPrice(
                label=PRODUCT_TITLES[product_type],
                amount=PRICES_STARS[product_type],
            )
        ],
        reply_markup=_pay_keyboard(),
    )


# ─── Pay callbacks from subscription menu ────────────────────────────────────

@router.callback_query(F.data.startswith("pay:"))
async def cb_pay_product(callback: CallbackQuery, state: FSMContext):
    product_type = callback.data.split(":", 1)[1]
    if product_type not in PRICES_STARS:
        await callback.answer()
        return
    await _start_payment(callback, product_type)


# ─── Pre-checkout: always approve ────────────────────────────────────────────

@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)


# ─── Successful payment: activate product ────────────────────────────────────

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, state: FSMContext):
    from handlers.spreads import SpreadState

    payment    = message.successful_payment
    product_type = payment.invoice_payload
    uid        = message.from_user.id
    stars      = payment.total_amount  # amount in XTR

    # Log payment to DB
    await create_payment(uid, stars, payment.telegram_payment_charge_id, product_type)
    await update_payment_status(payment.telegram_payment_charge_id, "succeeded")

    if product_type == "subscription":
        until = datetime.now(timezone.utc) + timedelta(days=30)
        await set_subscription(uid, until)
        await message.answer(SUBSCRIPTION_ACTIVE, reply_markup=back_to_main())

    elif product_type == "mirror":
        await state.set_state(SpreadState.waiting_question_mirror)
        await message.answer(PAYMENT_SUCCESS_MIRROR)

    elif product_type == "spread_year":
        await state.set_state(SpreadState.waiting_question_year)
        await message.answer(PAYMENT_SUCCESS_YEAR)

    elif product_type == "spread_compat":
        await state.set_state(SpreadState.waiting_question_compat)
        await message.answer(PAYMENT_SUCCESS_COMPAT)

    elif product_type == "ritual":
        await state.set_state(SpreadState.waiting_question_ritual)
        await message.answer(PAYMENT_SUCCESS_RITUAL)

    elif product_type == "journey":
        await message.answer(PAYMENT_SUCCESS_JOURNEY)
        # Deliver Day 1 immediately
        journey_id = await create_journey(uid)
        try:
            import asyncio
            from services import oracle
            from services.context import build_system_prompt
            user = await get_user(uid)
            recent = await get_recent_spreads(uid, limit=3)
            system_prompt = build_system_prompt(user or {}, recent)
            await asyncio.sleep(2)
            text = await oracle.generate_journey_day(1, system_prompt)
            spread_id = await save_spread(uid, "journey_1", "День 1: Твоя текущая энергия", text, None)
            intro = SPREAD_JOURNEY_DAY_INTRO.format(day=1)
            await message.answer(intro + text, reply_markup=reaction_keyboard(spread_id), parse_mode="Markdown")
        except Exception:
            pass
        await advance_journey(journey_id)
