from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Config:
    bot_token: str
    openai_api_key: str
    admin_id: int
    webhook_url: str
    database_url: str

    # Free limits per day
    free_card_of_day_limit: int = 1
    free_three_paths_limit: int = 1


# Prices in Telegram Stars (XTR)
PRICES_STARS = {
    "subscription":  30,
    "mirror":        50,
    "spread_year":   80,
    "spread_compat": 50,
    "ritual":       100,
}

# Invoice titles shown in Telegram payment UI (short, Velhar style)
PRODUCT_TITLES = {
    "subscription":  "Подписка VELHAR — 30 дней",
    "mirror":        "Зеркало судьбы",
    "spread_year":   "Год под звёздами",
    "spread_compat": "Нити судеб — совместимость",
    "ritual":        "Ритуал полнолуния",
}

# Invoice descriptions shown in Telegram payment UI
PRODUCT_DESCRIPTIONS = {
    "subscription":  "Безлимитный доступ к картам. Вселенная говорит без ограничений.",
    "mirror":        "Пять карт: суть, скрытые силы, препятствие, ресурс, итог.",
    "spread_year":   "Двенадцать карт — послание на каждый месяц года.",
    "spread_compat": "Карты откроют тайные нити между двумя душами.",
    "ritual":        "Семь карт в момент полной луны. Послание из глубин.",
}


def load_config() -> Config:
    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        admin_id=int(os.getenv("ADMIN_ID", "0")),
        webhook_url=os.getenv("WEBHOOK_URL", ""),
        database_url=os.getenv("DATABASE_URL", "velhar.db"),
    )


config = load_config()
