from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import PRICES_STARS

ZODIAC_SIGNS = [
    ("♈ Овен",     "Овен"),
    ("♉ Телец",    "Телец"),
    ("♊ Близнецы", "Близнецы"),
    ("♋ Рак",      "Рак"),
    ("♌ Лев",      "Лев"),
    ("♍ Дева",     "Дева"),
    ("♎ Весы",     "Весы"),
    ("♏ Скорпион", "Скорпион"),
    ("♐ Стрелец",  "Стрелец"),
    ("♑ Козерог",  "Козерог"),
    ("♒ Водолей",  "Водолей"),
    ("♓ Рыбы",     "Рыбы"),
]


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌌 Карта дня",    callback_data="spread:card_of_day"),
        InlineKeyboardButton(text="🔮 Три пути",      callback_data="spread:three_paths"),
    )
    builder.row(
        InlineKeyboardButton(text="✨ Подписка",      callback_data="menu:subscription"),
        InlineKeyboardButton(text="🌕 Ритуал",        callback_data="spread:ritual"),
    )
    builder.row(
        InlineKeyboardButton(text="🪞 Зеркало судьбы",    callback_data="spread:mirror"),
        InlineKeyboardButton(text="⭐ Год под звёздами",  callback_data="spread:year"),
    )
    builder.row(
        InlineKeyboardButton(text="💞 Совместимость", callback_data="spread:compat"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Позвать друга", callback_data="menu:referral"),
    )
    return builder.as_markup()


def zodiac_keyboard() -> InlineKeyboardMarkup:
    """12 zodiac sign buttons in a 3-column grid."""
    builder = InlineKeyboardBuilder()
    for i in range(0, len(ZODIAC_SIGNS), 3):
        row_items = ZODIAC_SIGNS[i:i + 3]
        builder.row(*[
            InlineKeyboardButton(text=label, callback_data=f"zodiac:{value}")
            for label, value in row_items
        ])
    return builder.as_markup()


def reaction_keyboard(spread_id: int) -> InlineKeyboardMarkup:
    """Reaction buttons shown after each spread result."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌌 Это обо мне",  callback_data=f"react:me_{spread_id}"),
        InlineKeyboardButton(text="🔮 Ещё вопрос",   callback_data="react:more"),
    )
    builder.row(
        InlineKeyboardButton(text="✨ Поделиться",    callback_data=f"react:share_{spread_id}"),
        InlineKeyboardButton(text="◀️ Меню",          callback_data="menu:main"),
    )
    return builder.as_markup()


def subscription_menu(is_subscribed: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_subscribed:
        builder.row(
            InlineKeyboardButton(
                text=f"💫 Подписка — {PRICES_STARS['subscription']} ⭐",
                callback_data="pay:subscription",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text=f"🪞 Зеркало судьбы — {PRICES_STARS['mirror']} ⭐",
            callback_data="pay:mirror",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"⭐ Год под звёздами — {PRICES_STARS['spread_year']} ⭐",
            callback_data="pay:spread_year",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"💞 Совместимость — {PRICES_STARS['spread_compat']} ⭐",
            callback_data="pay:spread_compat",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🌕 Ритуал полнолуния — {PRICES_STARS['ritual']} ⭐",
            callback_data="pay:ritual",
        ),
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


def cancel_input() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="menu:main"))
    return builder.as_markup()
