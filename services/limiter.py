from datetime import datetime, timezone
from database import (
    get_user,
    reset_daily_counters_if_needed,
    create_user,
)
from config import config


async def ensure_user(user_id: int, username: str | None):
    """Create user if not exists, then reset daily counters if new day."""
    await create_user(user_id, username)
    await reset_daily_counters_if_needed(user_id)


def _is_subscribed(user: dict) -> bool:
    if not user.get("is_subscribed"):
        return False
    until = user.get("subscription_until")
    if until is None:
        return False
    if isinstance(until, str):
        until_dt = datetime.fromisoformat(until)
    else:
        until_dt = until
    # Make aware if naive
    if until_dt.tzinfo is None:
        until_dt = until_dt.replace(tzinfo=timezone.utc)
    return until_dt > datetime.now(timezone.utc)


async def can_use_card_of_day(user_id: int) -> tuple[bool, str]:
    """
    Returns (allowed, reason).
    Бесплатно: 1 карта дня в сутки.
    Подписчики — безлимитно.
    """
    user = await get_user(user_id)
    if user is None:
        return False, "not_found"

    if _is_subscribed(user):
        return True, "subscribed"

    used = user.get("daily_free_used", 0)
    if used < config.free_card_of_day_limit:
        return True, "free"

    return False, "limit_reached"


async def can_use_three_paths(user_id: int) -> tuple[bool, str]:
    """
    Бесплатно: 1 расклад на три пути в сутки.
    Подписчики — безлимитно.
    """
    user = await get_user(user_id)
    if user is None:
        return False, "not_found"

    if _is_subscribed(user):
        return True, "subscribed"

    used = user.get("daily_free_used", 0)
    # Both free spreads share the same daily_free_used counter cap
    if used < config.free_card_of_day_limit + config.free_three_paths_limit:
        return True, "free"

    return False, "limit_reached"


async def can_use_month_spread(user_id: int) -> tuple[bool, str]:
    """Расклад на месяц — только для подписчиков."""
    user = await get_user(user_id)
    if user is None:
        return False, "not_found"
    if _is_subscribed(user):
        return True, "subscribed"
    return False, "need_subscription"


async def can_use_mirror(user_id: int) -> tuple[bool, str]:
    """Зеркало судьбы — разовая покупка (490₽)."""
    user = await get_user(user_id)
    if user is None:
        return False, "not_found"
    # Always requires payment — limiter just confirms user exists
    return True, "needs_payment"


async def can_use_year(user_id: int) -> tuple[bool, str]:
    """Год под звёздами — разовая покупка (990₽)."""
    user = await get_user(user_id)
    if user is None:
        return False, "not_found"
    return True, "needs_payment"


async def can_use_ritual(user_id: int) -> tuple[bool, str]:
    """Ритуал полнолуния — только в дни полнолуния ±2 дня."""
    from services.moon import is_near_fullmoon
    if not is_near_fullmoon():
        return False, "not_fullmoon"
    user = await get_user(user_id)
    if user is None:
        return False, "not_found"
    return True, "needs_payment"


def is_user_subscribed(user: dict) -> bool:
    return _is_subscribed(user)
