import aiosqlite
from datetime import datetime, date
from typing import Optional
from config import config


DB_PATH = config.database_url


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                username      TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_subscribed BOOLEAN DEFAULT FALSE,
                subscription_until TIMESTAMP,
                daily_free_used    INTEGER DEFAULT 0,
                daily_paid_mirror  INTEGER DEFAULT 0,
                daily_paid_year    INTEGER DEFAULT 0,
                last_reset_date    DATE,
                total_spreads      INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                amount       INTEGER,
                payment_id   TEXT,
                status       TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                product_type TEXT
            )
        """)
        # Add columns for existing DBs (idempotent migration)
        for col, definition in [
            ("daily_paid_mirror", "INTEGER DEFAULT 0"),
            ("daily_paid_year", "INTEGER DEFAULT 0"),
        ]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            except Exception:
                pass
        await db.commit()


# ─── User helpers ────────────────────────────────────────────────────────────

async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(user_id: int, username: Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO users (user_id, username, last_reset_date)
            VALUES (?, ?, ?)
            """,
            (user_id, username, date.today().isoformat()),
        )
        await db.commit()


async def update_username(user_id: int, username: Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET username = ? WHERE user_id = ?",
            (username, user_id),
        )
        await db.commit()


async def reset_daily_counters_if_needed(user_id: int):
    """Reset free/paid daily counters if it's a new calendar day."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT last_reset_date FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return
        today = date.today().isoformat()
        if row["last_reset_date"] != today:
            await db.execute(
                """
                UPDATE users
                SET daily_free_used = 0,
                    daily_paid_mirror = 0,
                    daily_paid_year = 0,
                    last_reset_date = ?
                WHERE user_id = ?
                """,
                (today, user_id),
            )
            await db.commit()


async def increment_free_used(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET daily_free_used = daily_free_used + 1, total_spreads = total_spreads + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def increment_total_spreads(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET total_spreads = total_spreads + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def increment_paid_mirror(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET daily_paid_mirror = daily_paid_mirror + 1, total_spreads = total_spreads + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def increment_paid_year(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET daily_paid_year = daily_paid_year + 1, total_spreads = total_spreads + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def set_subscription(user_id: int, until: datetime):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_subscribed = TRUE, subscription_until = ? WHERE user_id = ?",
            (until.isoformat(), user_id),
        )
        await db.commit()


# ─── Payment helpers ──────────────────────────────────────────────────────────

async def create_payment(
    user_id: int,
    amount: int,
    payment_id: str,
    product_type: str,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO payments (user_id, amount, payment_id, status, product_type)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (user_id, amount, payment_id, product_type),
        )
        await db.commit()
        return cursor.lastrowid


async def update_payment_status(payment_id: str, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status = ? WHERE payment_id = ?",
            (status, payment_id),
        )
        await db.commit()


async def get_payment_by_id(payment_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE payment_id = ?", (payment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ─── Stats helpers ────────────────────────────────────────────────────────────

async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT COUNT(*) as cnt FROM users") as cur:
            total_users = (await cur.fetchone())["cnt"]

        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE is_subscribed = TRUE AND subscription_until > datetime('now')"
        ) as cur:
            active_subs = (await cur.fetchone())["cnt"]

        month_start = date.today().replace(day=1).isoformat()
        async with db.execute(
            "SELECT COALESCE(SUM(amount), 0) as revenue FROM payments WHERE status = 'succeeded' AND created_at >= ?",
            (month_start,),
        ) as cur:
            month_revenue = (await cur.fetchone())["revenue"]

        today = date.today().isoformat()
        async with db.execute(
            "SELECT COALESCE(SUM(total_spreads), 0) as ts FROM users WHERE last_reset_date = ?",
            (today,),
        ) as cur:
            # total_spreads is lifetime; count today's via daily counters
            pass

        async with db.execute(
            "SELECT COALESCE(SUM(daily_free_used + daily_paid_mirror + daily_paid_year), 0) as cnt FROM users WHERE last_reset_date = ?",
            (today,),
        ) as cur:
            spreads_today = (await cur.fetchone())["cnt"]

        async with db.execute(
            "SELECT COALESCE(SUM(total_spreads), 0) as cnt FROM users"
        ) as cur:
            spreads_total = (await cur.fetchone())["cnt"]

    return {
        "total_users": total_users,
        "active_subs": active_subs,
        "month_revenue": month_revenue,
        "spreads_today": spreads_today,
        "spreads_total": spreads_total,
    }
