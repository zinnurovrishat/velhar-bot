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
        InlineKeyboardButton(text="🌌 Карта дня",         callback_data="spread_day"),
        InlineKeyboardButton(text="🔮 Задать вопрос",      callback_data="spread_question"),
    )
    builder.row(
        InlineKeyboardButton(text="✨ Глубокий расклад",   callback_data="spread_deep"),
        InlineKeyboardButton(text="🌙 Лунный путь",          callback_data="ritual"),
    )
    builder.row(
        InlineKeyboardButton(text="🌟 Путь озарения — 7 дней", callback_data="menu:journey"),
    )
    builder.row(
        InlineKeyboardButton(text="🌅 Карта каждое утро",  callback_data="menu:daily_notify"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Позвать друга",      callback_data="referral"),
        InlineKeyboardButton(text="👁 Кто такой Велхар",   callback_data="about"),
    )
    return builder.as_markup()


def journey_intro_menu() -> InlineKeyboardMarkup:
    """Вводный экран перед покупкой пути."""
    from config import PRICES_STARS
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"🌟 Начать путь — {PRICES_STARS['journey']} ⭐",
            callback_data="spread:journey",
        )
    )
    builder.row(InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main"))
    return builder.as_markup()


def daily_notify_menu(enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if enabled:
        builder.row(InlineKeyboardButton(text="🔕 Отключить", callback_data="notify:daily_off"))
    else:
        builder.row(InlineKeyboardButton(text="🌅 Включить", callback_data="notify:daily_on"))
    builder.row(InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"))
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
            text=f"✨ Глубокий расклад — {PRICES_STARS['mirror']} ⭐",
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
            text=f"🌕 Лунное послание — {PRICES_STARS['ritual']} ⭐",
            callback_data="pay:ritual",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🌟 Путь озарения — {PRICES_STARS['journey']} ⭐",
            callback_data="menu:journey",
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
        InlineKeyboardButton(text="✨ Открыть доступ", callback_data="menu:subscription"),
        InlineKeyboardButton(text="🌙 Вернуться завтра", callback_data="menu:main"),
    )
    return builder.as_markup()


def cancel_input() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="menu:main"))
    return builder.as_markup()


def upsell_deep_reading() -> InlineKeyboardMarkup:
    """Показывается после бесплатного расклада — мягкий намёк на платный."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"🔮 Открыть глубокий расклад — {PRICES_STARS['mirror']} ⭐",
            callback_data="spread:mirror",
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")
    )
    return builder.as_markup()


def upsell_journey() -> InlineKeyboardMarkup:
    """После первых раскладов — предложить 7-дневный путь."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"🌟 Начать 7-дневный путь — {PRICES_STARS['journey']} ⭐",
            callback_data="menu:journey",
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")
    )
    return builder.as_markup()
