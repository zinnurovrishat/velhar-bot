from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Config:
    bot_token: str
    openai_api_key: str
    crypto_bot_token: str
    admin_id: int
    webhook_url: str
    database_url: str

    # Free limits per day
    free_card_of_day_limit: int = 1
    free_three_paths_limit: int = 1


# Fixed USDT prices
PRICES_USDT = {
    "subscription": 3.5,
    "mirror":       5.5,
    "spread_year":  11.0,
    "ritual":       17.0,
}

# Fixed TON prices (≈ 1 TON ~ 5.5 USD)
PRICES_TON = {
    "subscription": 0.7,
    "mirror":       1.0,
    "spread_year":  2.0,
    "ritual":       3.1,
}


def load_config() -> Config:
    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        crypto_bot_token=os.getenv("CRYPTO_BOT_TOKEN", ""),
        admin_id=int(os.getenv("ADMIN_ID", "0")),
        webhook_url=os.getenv("WEBHOOK_URL", ""),
        database_url=os.getenv("DATABASE_URL", "velhar.db"),
    )


config = load_config()
