import uuid
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from config import config
from database import (
    create_payment,
    get_payment_by_id,
    update_payment_status,
    set_subscription,
    get_user,
)
from keyboards.menus import payment_link_menu, back_to_main, subscription_menu
from services.limiter import is_user_subscribed
from texts.messages import (
    PAYMENT_PENDING,
    PAYMENT_SUCCESS_MIRROR,
    PAYMENT_SUCCESS_YEAR,
    PAYMENT_SUCCESS_RITUAL,
    PAYMENT_NOT_FOUND,
    PAYMENT_ERROR,
    SUBSCRIPTION_ACTIVE,
)

router = Router()

# ─── Product catalogue ────────────────────────────────────────────────────────

PRODUCTS = {
    "subscription": {
        "label": "Подписка VELHAR на 30 дней",
        "amount": config.price_subscription,
    },
    "mirror": {
        "label": "Зеркало судьбы — глубокий расклад",
        "amount": config.price_mirror,
    },
    "spread_year": {
        "label": "Год под звёздами — расклад на год",
        "amount": config.price_year,
    },
    "ritual": {
        "label": "Ритуал полнолуния",
        "amount": config.price_ritual,
    },
}


def _build_yookassa_payment(product_type: str, user_id: int) -> dict | None:
    """
    Create a YooKassa payment and return (payment_id, confirmation_url).
    Returns None if YooKassa is not configured (useful for local testing).
    """
    if not config.yookassa_shop_id or not config.yookassa_secret_key:
        return None

    try:
        from yookassa import Configuration, Payment as YKPayment

        Configuration.account_id = config.yookassa_shop_id
        Configuration.secret_key = config.yookassa_secret_key

        product = PRODUCTS[product_type]
        idempotency_key = str(uuid.uuid4())

        payment = YKPayment.create(
            {
                "amount": {"value": str(product["amount"]) + ".00", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/{config.webhook_url.split('/')[-1]}",
                },
                "capture": True,
                "description": product["label"],
                "metadata": {"user_id": user_id, "product_type": product_type},
            },
            idempotency_key,
        )
        return {"payment_id": payment.id, "url": payment.confirmation.confirmation_url}
    except Exception as e:
        print(f"YooKassa error: {e}")
        return None


# ─── Shared payment starter (called from spreads.py) ─────────────────────────

async def _start_payment(callback: CallbackQuery, product_type: str):
    """Initiate payment flow for any product."""
    uid = callback.from_user.id
    product = PRODUCTS.get(product_type)
    if not product:
        await callback.answer("Неизвестный продукт", show_alert=True)
        return

    yk_data = _build_yookassa_payment(product_type, uid)

    if yk_data:
        payment_id = yk_data["payment_id"]
        url = yk_data["url"]
        await create_payment(uid, product["amount"], payment_id, product_type)
        await callback.message.edit_text(
            PAYMENT_PENDING,
            reply_markup=payment_link_menu(url),
            parse_mode="Markdown",
        )
    else:
        # YooKassa not configured — show stub message for local dev
        await callback.message.edit_text(
            f"💳 *{product['label']}*\n\n"
            f"Стоимость: *{product['amount']}₽*\n\n"
            "_YooKassa не настроена. В продакшне здесь появится ссылка на оплату._",
            reply_markup=back_to_main(),
            parse_mode="Markdown",
        )

    await callback.answer()


# ─── Pay callbacks from subscription menu ────────────────────────────────────

@router.callback_query(F.data.startswith("pay:") & ~F.data.startswith("pay:confirm") & ~F.data.startswith("pay:check"))
async def cb_pay_product(callback: CallbackQuery, state: FSMContext):
    product_type = callback.data.split(":", 1)[1]
    if product_type not in PRODUCTS:
        await callback.answer()
        return
    await _start_payment(callback, product_type)


# ─── Check payment status ─────────────────────────────────────────────────────

@router.callback_query(F.data == "pay:check")
async def cb_pay_check(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id

    # Find the most recent pending payment for this user
    import aiosqlite
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

    payment_id = payment_row["payment_id"]
    product_type = payment_row["product_type"]

    # Check with YooKassa
    status = await _check_yookassa_status(payment_id)

    if status == "succeeded":
        await update_payment_status(payment_id, "succeeded")
        await _handle_successful_payment(callback, uid, product_type, state)
    elif status == "canceled":
        await update_payment_status(payment_id, "canceled")
        await callback.message.edit_text(
            "Платёж отменён. Если это ошибка — попробуй снова.",
            reply_markup=back_to_main(),
        )
    else:
        await callback.answer(
            "Платёж ещё не подтверждён. Подожди немного и попробуй снова.",
            show_alert=True,
        )


async def _check_yookassa_status(payment_id: str) -> str:
    """Return YooKassa payment status string, or 'pending' on error."""
    if not config.yookassa_shop_id:
        return "pending"
    try:
        from yookassa import Configuration, Payment as YKPayment

        Configuration.account_id = config.yookassa_shop_id
        Configuration.secret_key = config.yookassa_secret_key
        payment = YKPayment.find_one(payment_id)
        return payment.status
    except Exception as e:
        print(f"YooKassa check error: {e}")
        return "pending"


async def _handle_successful_payment(
    callback: CallbackQuery,
    uid: int,
    product_type: str,
    state: FSMContext,
):
    """Activate subscription or prompt for spread question."""
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
            PAYMENT_SUCCESS_MIRROR, reply_markup=None, parse_mode="Markdown"
        )

    elif product_type == "spread_year":
        await state.set_state(SpreadState.waiting_question_year)
        await callback.message.edit_text(
            PAYMENT_SUCCESS_YEAR, reply_markup=None, parse_mode="Markdown"
        )

    elif product_type == "ritual":
        await state.set_state(SpreadState.waiting_question_ritual)
        await callback.message.edit_text(
            PAYMENT_SUCCESS_RITUAL, reply_markup=None, parse_mode="Markdown"
        )

    await callback.answer()


# ─── YooKassa Webhook handler (called from bot.py web server) ─────────────────

async def process_webhook_event(event_data: dict, bot):
    """Called by the aiohttp webhook route."""
    try:
        event_type = event_data.get("event")
        obj = event_data.get("object", {})
        payment_id = obj.get("id")
        status = obj.get("status")

        if event_type != "payment.succeeded" or status != "succeeded":
            return

        payment_row = await get_payment_by_id(payment_id)
        if not payment_row or payment_row["status"] == "succeeded":
            return

        await update_payment_status(payment_id, "succeeded")

        uid = payment_row["user_id"]
        product_type = payment_row["product_type"]

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

    except Exception as e:
        print(f"Webhook processing error: {e}")
