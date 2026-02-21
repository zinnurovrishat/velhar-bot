from datetime import datetime, timedelta, timezone

import aiosqlite
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from config import config, PRICES_USDT, PRICES_TON
from database import (
    create_payment,
    update_payment_status,
    get_payment_by_id,
    set_subscription,
)
from keyboards.menus import (
    back_to_main,
    currency_select_menu,
    payment_link_menu,
)
from services import cryptopay
from texts.messages import (
    SUBSCRIPTION_ACTIVE,
    PAYMENT_SUCCESS_MIRROR,
    PAYMENT_SUCCESS_YEAR,
    PAYMENT_SUCCESS_RITUAL,
)

router = Router()

# ─── Product catalogue ────────────────────────────────────────────────────────

PRODUCTS = {
    "subscription": "Подписка VELHAR на 30 дней",
    "mirror":       "Зеркало судьбы — глубокий расклад",
    "spread_year":  "Год под звёздами — расклад на год",
    "ritual":       "Ритуал полнолуния",
}


# ─── Step 1: choose currency (called from spreads.py & subscription menu) ────

async def _start_payment(callback: CallbackQuery, product_type: str):
    """Show currency selection screen."""
    if product_type not in PRODUCTS:
        await callback.answer("Неизвестный продукт", show_alert=True)
        return

    usdt = PRICES_USDT[product_type]
    ton  = PRICES_TON[product_type]
    label = PRODUCTS[product_type]

    await callback.message.edit_text(
        f"💫 *{label}*\n\n"
        f"Выбери валюту оплаты:\n\n"
        f"• USDT — `{usdt}` USDT\n"
        f"• TON  — `{ton}` TON",
        reply_markup=currency_select_menu(product_type),
        parse_mode="Markdown",
    )
    await callback.answer()


# ─── Step 2: create invoice after currency chosen ────────────────────────────

@router.callback_query(F.data.startswith("pay:currency:"))
async def cb_currency_selected(callback: CallbackQuery, state: FSMContext):
    # callback_data: pay:currency:USDT:subscription
    _, _, asset, product_type = callback.data.split(":", 3)
    uid = callback.from_user.id

    if product_type not in PRODUCTS:
        await callback.answer()
        return

    amount = PRICES_USDT[product_type] if asset == "USDT" else PRICES_TON[product_type]
    label  = PRODUCTS[product_type]

    await callback.message.edit_text(
        "Создаю счёт... ✨", reply_markup=None
    )

    try:
        invoice = await cryptopay.create_invoice(
            asset=asset,
            amount=amount,
            description=label,
            payload=f"{uid}:{product_type}",
            expires_in=3600,
        )
    except Exception as e:
        await callback.message.edit_text(
            "Что-то нарушило платёжный поток... Попробуй позже.",
            reply_markup=back_to_main(),
        )
        return

    invoice_id  = invoice["invoice_id"]
    pay_url     = invoice["bot_invoice_url"]

    # Save to DB (store invoice_id as payment_id)
    await create_payment(uid, amount, str(invoice_id), product_type)

    await callback.message.edit_text(
        f"💫 *{label}*\n\n"
        f"Сумма: *{amount} {asset}*\n\n"
        "Перейди по ссылке и оплати через @CryptoBot.\n"
        "После оплаты нажми «Я оплатил» — и карты заговорят.",
        reply_markup=payment_link_menu(pay_url),
        parse_mode="Markdown",
    )
    await callback.answer()


# ─── Pay callbacks from subscription menu ────────────────────────────────────

@router.callback_query(
    F.data.startswith("pay:")
    & ~F.data.startswith("pay:currency:")
    & ~F.data.startswith("pay:check")
)
async def cb_pay_product(callback: CallbackQuery, state: FSMContext):
    product_type = callback.data.split(":", 1)[1]
    if product_type not in PRODUCTS:
        await callback.answer()
        return
    await _start_payment(callback, product_type)


# ─── Step 3: user pressed «Я оплатил» ────────────────────────────────────────

@router.callback_query(F.data == "pay:check")
async def cb_pay_check(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id

    async with aiosqlite.connect(config.database_url) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
            (uid,),
        ) as cursor:
            row = await cursor.fetchone()
            payment_row = dict(row) if row else None

    if not payment_row:
        await callback.answer("Ожидающий платёж не найден", show_alert=True)
        return

    invoice_id   = int(payment_row["payment_id"])
    product_type = payment_row["product_type"]

    try:
        invoice = await cryptopay.get_invoice(invoice_id)
        status  = invoice.get("status")
    except Exception:
        await callback.answer(
            "Не удалось проверить статус. Попробуй чуть позже.",
            show_alert=True,
        )
        return

    if status == "paid":
        await update_payment_status(str(invoice_id), "succeeded")
        await _handle_successful_payment(callback, uid, product_type, state)
    elif status == "expired":
        await update_payment_status(str(invoice_id), "expired")
        await callback.message.edit_text(
            "Время оплаты истекло... Создай новый счёт.",
            reply_markup=back_to_main(),
        )
    else:
        await callback.answer(
            "Оплата ещё не получена. Подожди немного и попробуй снова.",
            show_alert=True,
        )


# ─── Activate product after successful payment ────────────────────────────────

async def _handle_successful_payment(
    callback: CallbackQuery,
    uid: int,
    product_type: str,
    state: FSMContext,
):
    from handlers.spreads import SpreadState

    if product_type == "subscription":
        until = datetime.now(timezone.utc) + timedelta(days=30)
        await set_subscription(uid, until)
        await callback.message.edit_text(
            SUBSCRIPTION_ACTIVE, reply_markup=back_to_main(), parse_mode="Markdown"
        )

    elif product_type == "mirror":
        await state.set_state(SpreadState.waiting_question_mirror)
        await callback.message.edit_text(
            PAYMENT_SUCCESS_MIRROR, parse_mode="Markdown"
        )

    elif product_type == "spread_year":
        await state.set_state(SpreadState.waiting_question_year)
        await callback.message.edit_text(
            PAYMENT_SUCCESS_YEAR, parse_mode="Markdown"
        )

    elif product_type == "ritual":
        await state.set_state(SpreadState.waiting_question_ritual)
        await callback.message.edit_text(
            PAYMENT_SUCCESS_RITUAL, parse_mode="Markdown"
        )

    await callback.answer()


# ─── CryptoPay Webhook (called from bot.py) ───────────────────────────────────

async def process_cryptopay_webhook(body: bytes, signature: str, bot) -> bool:
    """
    Verify and handle an incoming CryptoPay webhook.
    Returns True if handled successfully.
    """
    if not cryptopay.verify_webhook(body, config.crypto_bot_token, signature):
        return False

    import json
    data   = json.loads(body)
    if data.get("update_type") != "invoice_paid":
        return True

    invoice      = data.get("payload", {})
    invoice_id   = str(invoice.get("invoice_id", ""))
    raw_payload  = invoice.get("payload", "")   # "{uid}:{product_type}"

    payment_row = await get_payment_by_id(invoice_id)
    if payment_row and payment_row["status"] != "succeeded":
        await update_payment_status(invoice_id, "succeeded")

        uid_str, product_type = raw_payload.split(":", 1)
        uid = int(uid_str)

        if product_type == "subscription":
            until = datetime.now(timezone.utc) + timedelta(days=30)
            await set_subscription(uid, until)
            await bot.send_message(uid, SUBSCRIPTION_ACTIVE, reply_markup=back_to_main())

        elif product_type == "mirror":
            await bot.send_message(uid, PAYMENT_SUCCESS_MIRROR, parse_mode="Markdown")

        elif product_type == "spread_year":
            await bot.send_message(uid, PAYMENT_SUCCESS_YEAR, parse_mode="Markdown")

        elif product_type == "ritual":
            await bot.send_message(uid, PAYMENT_SUCCESS_RITUAL, parse_mode="Markdown")

    return True
