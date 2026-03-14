"""APScheduler-based reminder jobs for VELHAR bot."""
import logging
import random
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import (
    get_inactive_users,
    get_all_active_users,
    get_users_with_spreads_this_week,
    get_pending_journey_deliveries,
    advance_journey,
    save_spread,
    get_user,
    get_recent_spreads,
    get_daily_notify_users,
    get_users_streak_at_risk,
)
from services.context import get_days_until_fullmoon

logger = logging.getLogger(__name__)
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

_scheduler: AsyncIOScheduler | None = None
_bot = None


def setup_scheduler(bot) -> AsyncIOScheduler:
    """Create and configure the scheduler. Call start() separately."""
    global _scheduler, _bot
    _bot = bot
    _scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)

    # Daily at 19:00 MSK — nudge inactive users (3+ days silent)
    _scheduler.add_job(
        _remind_inactive,
        CronTrigger(hour=19, minute=0, timezone=MOSCOW_TZ),
        id="remind_inactive",
        replace_existing=True,
    )

    # Daily at 10:00 MSK — check if full moon is 2 days away
    _scheduler.add_job(
        _fullmoon_reminder,
        CronTrigger(hour=10, minute=0, timezone=MOSCOW_TZ),
        id="fullmoon_reminder",
        replace_existing=True,
    )

    # Every Sunday at 20:00 MSK — weekly summary
    _scheduler.add_job(
        _weekly_summary,
        CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=MOSCOW_TZ),
        id="weekly_summary",
        replace_existing=True,
    )

    # Daily at 13:00 MSK — deliver next Journey day to users on a 7-day path
    _scheduler.add_job(
        _deliver_journey_days,
        CronTrigger(hour=13, minute=0, timezone=MOSCOW_TZ),
        id="deliver_journey_days",
        replace_existing=True,
    )

    # Daily at 9:00 MSK — send morning card to opted-in users
    _scheduler.add_job(
        _send_daily_cards,
        CronTrigger(hour=9, minute=0, timezone=MOSCOW_TZ),
        id="send_daily_cards",
        replace_existing=True,
    )

    # Daily at 20:30 MSK — warn users whose streak is about to break
    _scheduler.add_job(
        _streak_warning,
        CronTrigger(hour=20, minute=30, timezone=MOSCOW_TZ),
        id="streak_warning",
        replace_existing=True,
    )

    return _scheduler


# ─── Job implementations ──────────────────────────────────────────────────────

async def _remind_inactive():
    """Send a nudge to users who haven't interacted in 3+ days."""
    if not _bot:
        return

    messages = [
        "🌌 *VELHAR зовёт тебя...*\n\n"
        "Звёзды не забыли о тебе. Что тревожит душу? "
        "Приди, и карты откроют путь.",

        "🔮 *Послание из глубин...*\n\n"
        "Энергии дня готовы раскрыться именно для тебя. "
        "Не дай потоку пройти мимо.",

        "✨ *Нити судьбы ждут...*\n\n"
        "Карты хранят для тебя послание. "
        "Загляни в VELHAR и услышь голос звёзд.",
    ]

    from keyboards.menus import main_menu
    users = await get_inactive_users(days=3)
    logger.info(f"[reminders] Inactive users to nudge: {len(users)}")

    for user in users:
        try:
            await _bot.send_message(
                user["user_id"],
                random.choice(messages),
                reply_markup=main_menu(),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.debug(f"Cannot notify {user['user_id']}: {e}")


async def _fullmoon_reminder():
    """Warn active users 2 days before full moon."""
    if not _bot:
        return

    days = get_days_until_fullmoon()
    if days != 2:
        return

    users = await get_all_active_users()
    logger.info(f"[reminders] Full-moon reminder → {len(users)} users")

    for user in users:
        try:
            await _bot.send_message(
                user["user_id"],
                "🌕 *Полнолуние — через 2 дня*\n\n"
                "Энергии луны достигают пика... "
                "Ритуал полнолуния откроет тебе врата в глубинные потоки судьбы.\n\n"
                "Приготовься.",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.debug(f"Cannot notify {user['user_id']}: {e}")


async def _weekly_summary():
    """Send weekly recap to users who had spreads this week."""
    if not _bot:
        return

    users = await get_users_with_spreads_this_week()
    logger.info(f"[reminders] Weekly summary → {len(users)} users")

    for user in users:
        name  = user.get("name") or "путник"
        total = user.get("total_spreads") or 0
        try:
            await _bot.send_message(
                user["user_id"],
                f"🌟 *Итоги недели, {name}*\n\n"
                f"За эту неделю ты обращался к звёздам и получал послания.\n"
                f"Всего раскладов пройдено: *{total}*\n\n"
                f"Звёзды продолжают наблюдать за твоим путём. "
                f"Новая неделя несёт новые энергии — приходи за советом.",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.debug(f"Cannot notify {user['user_id']}: {e}")


async def _deliver_journey_days():
    """Отправляет следующий день пути пользователям на 7-дневном маршруте."""
    if not _bot:
        return

    pending = await get_pending_journey_deliveries()
    logger.info(f"[reminders] Journey delivery → {len(pending)} pending")

    from services import oracle
    from services.context import build_system_prompt
    from keyboards.menus import reaction_keyboard
    from texts.messages import SPREAD_JOURNEY_DAY_INTRO

    for journey in pending:
        uid = journey["user_id"]
        day = journey["current_day"]
        journey_id = journey["id"]
        try:
            user = await get_user(uid)
            recent = await get_recent_spreads(uid, limit=3)
            system_prompt = build_system_prompt(user or {}, recent)
            text = await oracle.generate_journey_day(day, system_prompt)
            spread_id = await save_spread(uid, f"journey_{day}", f"День {day}", text, None)
            intro = SPREAD_JOURNEY_DAY_INTRO.format(day=day)
            await _bot.send_message(
                uid,
                intro + text,
                reply_markup=reaction_keyboard(spread_id),
                parse_mode="Markdown",
            )
            await advance_journey(journey_id)
            if day == 7:
                await _bot.send_message(
                    uid,
                    "🌟 *Твой путь завершён.*\n\n"
                    "Семь дней. Семь карт. Семь откровений.\n\n"
                    "Путь, который ты прошёл через эти послания — "
                    "неси его дальше. Звёзды говорили с тобой.",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.debug(f"Journey delivery failed for {uid}: {e}")


async def _send_daily_cards():
    """Отправляет утреннюю карту дня пользователям, подписавшимся на уведомления."""
    if not _bot:
        return

    users = await get_daily_notify_users()
    logger.info(f"[reminders] Daily cards → {len(users)} users")

    from services import oracle
    from services.context import build_system_prompt
    from keyboards.menus import reaction_keyboard
    from texts.messages import SPREAD_CARD_OF_DAY_INTRO

    for user in users:
        uid = user["user_id"]
        try:
            recent = await get_recent_spreads(uid, limit=3)
            system_prompt = build_system_prompt(user, recent)
            text = await oracle.generate_card_of_day("карта дня", system_prompt)
            spread_id = await save_spread(uid, "spread_day", "карта дня", text, None)
            await _bot.send_message(
                uid,
                SPREAD_CARD_OF_DAY_INTRO + text,
                reply_markup=reaction_keyboard(spread_id),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.debug(f"Daily card failed for {uid}: {e}")


async def _streak_warning():
    """Напоминает пользователям, что серия скоро прервётся."""
    if not _bot:
        return

    users = await get_users_streak_at_risk()
    logger.info(f"[reminders] Streak at risk → {len(users)} users")

    from keyboards.menus import main_menu

    for user in users:
        streak = user.get("current_streak", 0)
        if not streak:
            continue
        try:
            await _bot.send_message(
                user["user_id"],
                f"🔥 *Серия под угрозой*\n\n"
                f"Ты {streak} дней подряд с Велхаром.\n"
                f"До полуночи — вытяни карту, чтобы не прервать путь.",
                reply_markup=main_menu(),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.debug(f"Streak warning failed for {user['user_id']}: {e}")
