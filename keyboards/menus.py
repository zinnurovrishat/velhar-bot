from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import PRICES_USDT, PRICES_TON


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌌 Карта дня", callback_data="spread:card_of_day"),
        InlineKeyboardButton(text="🔮 Три пути", callback_data="spread:three_paths"),
    )
    builder.row(
        InlineKeyboardButton(text="✨ Подписка", callback_data="menu:subscription"),
        InlineKeyboardButton(text="🌕 Ритуал", callback_data="spread:ritual"),
    )
    builder.row(
        InlineKeyboardButton(text="🪞 Зеркало судьбы", callback_data="spread:mirror"),
        InlineKeyboardButton(text="⭐ Год под звёздами", callback_data="spread:year"),
    )
    return builder.as_markup()


def subscription_menu(is_subscribed: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_subscribed:
        builder.row(
            InlineKeyboardButton(
                text=f"💫 Подписка — {PRICES_USDT['subscription']} USDT / {PRICES_TON['subscription']} TON",
                callback_data="pay:subscription",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text=f"🪞 Зеркало судьбы — {PRICES_USDT['mirror']} USDT",
            callback_data="pay:mirror",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"⭐ Год под звёздами — {PRICES_USDT['spread_year']} USDT",
            callback_data="pay:spread_year",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🌕 Ритуал полнолуния — {PRICES_USDT['ritual']} USDT",
            callback_data="pay:ritual",
        ),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main"),
    )
    return builder.as_markup()


def currency_select_menu(product_type: str) -> InlineKeyboardMarkup:
    """Choose USDT or TON before creating invoice."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"💵 USDT — {PRICES_USDT[product_type]}",
            callback_data=f"pay:currency:USDT:{product_type}",
        ),
        InlineKeyboardButton(
            text=f"💎 TON — {PRICES_TON[product_type]}",
            callback_data=f"pay:currency:TON:{product_type}",
        ),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:subscription"))
    return builder.as_markup()


def payment_link_menu(url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Оплатить через CryptoBot", url=url))
    builder.row(InlineKeyboardButton(text="✅ Я оплатил", callback_data="pay:check"))
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def back_to_main() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def limit_reached_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✨ Открыть полный доступ", callback_data="menu:subscription")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu:main")
    )
    return builder.as_markup()


def cancel_input() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="menu:main"))
    return builder.as_markup()
