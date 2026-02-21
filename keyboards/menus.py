from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


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
                text="💫 Оформить подписку — 299₽/мес",
                callback_data="pay:subscription",
            )
        )
    builder.row(
        InlineKeyboardButton(text="🪞 Зеркало судьбы — 490₽", callback_data="pay:mirror"),
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Год под звёздами — 990₽", callback_data="pay:year"),
    )
    builder.row(
        InlineKeyboardButton(text="🌕 Ритуал полнолуния — 1490₽", callback_data="pay:ritual"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main"),
    )
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


def pay_confirm_menu(product_type: str, amount: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"💳 Оплатить {amount}₽",
            callback_data=f"pay:confirm:{product_type}",
        )
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:subscription"))
    return builder.as_markup()


def payment_link_menu(url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Перейти к оплате", url=url))
    builder.row(InlineKeyboardButton(text="✅ Я оплатил", callback_data="pay:check"))
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def cancel_input() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="menu:main"))
    return builder.as_markup()
