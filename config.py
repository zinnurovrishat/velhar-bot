from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Config:
    bot_token: str
    openai_api_key: str
    yookassa_shop_id: str
    yookassa_secret_key: str
    admin_id: int
    webhook_url: str
    database_url: str

    # Pricing (in RUB, stored as kopecks for YooKassa)
    price_subscription: int = 299
    price_mirror: int = 490
    price_year: int = 990
    price_ritual: int = 1490

    # Free limits per day
    free_card_of_day_limit: int = 1
    free_three_paths_limit: int = 1


def load_config() -> Config:
    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        yookassa_shop_id=os.getenv("YOOKASSA_SHOP_ID", ""),
        yookassa_secret_key=os.getenv("YOOKASSA_SECRET_KEY", ""),
        admin_id=int(os.getenv("ADMIN_ID", "0")),
        webhook_url=os.getenv("WEBHOOK_URL", ""),
        database_url=os.getenv("DATABASE_URL", "velhar.db"),
    )


config = load_config()
