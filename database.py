import secrets
import aiosqlite
from datetime import datetime, date, timedelta
from typing import Optional
from config import config


DB_PATH = config.database_url

# ─── Schema init + migrations ─────────────────────────────────────────────────

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id                    INTEGER PRIMARY KEY,
                username                   TEXT,
                name                       TEXT,
                zodiac_sign                TEXT,
                referral_code              TEXT UNIQUE,
                referred_by                INTEGER,
                referral_bonuses_available INTEGER DEFAULT 0,
                last_active                DATETIME,
                created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_subscribed              BOOLEAN DEFAULT FALSE,
                subscription_until         TIMESTAMP,
                daily_free_used            INTEGER DEFAULT 0,
                daily_paid_mirror          INTEGER DEFAULT 0,
                daily_paid_year            INTEGER DEFAULT 0,
                last_reset_date            DATE,
                total_spreads              INTEGER DEFAULT 0
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS spreads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                spread_type TEXT NOT NULL,
                question    TEXT,
                response    TEXT NOT NULL,
                summary     TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        # Idempotent migrations for users table
        _new_cols = [
            ("daily_paid_mirror",          "INTEGER DEFAULT 0"),
            ("daily_paid_year",            "INTEGER DEFAULT 0"),
            ("name",                       "TEXT"),
            ("zodiac_sign",                "TEXT"),
            ("referral_code",              "TEXT"),
            ("referred_by",                "INTEGER"),
            ("referral_bonuses_available", "INTEGER DEFAULT 0"),
            ("last_active",                "DATETIME"),
            ("ai_question_count",          "INTEGER DEFAULT 0"),
            ("spreads_since_memory",       "INTEGER DEFAULT 0"),
            ("velhar_state",               "TEXT DEFAULT 'calm'"),
        ]
        for col, definition in _new_cols:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            except Exception:
                pass
        await db.commit()


# ─── User helpers ─────────────────────────────────────────────────────────────

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
            INSERT OR IGNORE INTO users (user_id, username, last_reset_date, last_active)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, username, date.today().isoformat(), datetime.utcnow().isoformat()),
        )
        await db.commit()


async def update_username(user_id: int, username: Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET username = ? WHERE user_id = ?",
            (username, user_id),
        )
        await db.commit()


async def update_user_name(user_id: int, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET name = ? WHERE user_id = ?",
            (name, user_id),
        )
        await db.commit()


async def update_user_zodiac(user_id: int, zodiac: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET zodiac_sign = ? WHERE user_id = ?",
            (zodiac, user_id),
        )
        await db.commit()


async def update_last_active(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()


async def reset_daily_counters_if_needed(user_id: int):
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


# ─── Referral helpers ─────────────────────────────────────────────────────────

async def generate_and_save_referral_code(user_id: int) -> str:
    """Generate a unique referral code and store it. Returns the code."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if already has one
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT referral_code FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        if row and row["referral_code"]:
            return row["referral_code"]

        for _ in range(10):
            code = secrets.token_urlsafe(6).upper()[:8]
            async with db.execute(
                "SELECT user_id FROM users WHERE referral_code = ?", (code,)
            ) as cur:
                exists = await cur.fetchone()
            if not exists:
                await db.execute(
                    "UPDATE users SET referral_code = ? WHERE user_id = ?",
                    (code, user_id),
                )
                await db.commit()
                return code
    return secrets.token_urlsafe(8).upper()


async def find_user_by_referral_code(code: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE referral_code = ?", (code.upper(),)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def set_referred_by(user_id: int, referrer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET referred_by = ? WHERE user_id = ? AND referred_by IS NULL",
            (referrer_id, user_id),
        )
        await db.commit()


async def count_referrals(referrer_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE referred_by = ?", (referrer_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def add_referral_bonus(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET referral_bonuses_available = referral_bonuses_available + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def use_referral_bonus(user_id: int) -> bool:
    """Consume one referral bonus. Returns True if bonus was available."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT referral_bonuses_available FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row or (row["referral_bonuses_available"] or 0) < 1:
            return False
        await db.execute(
            "UPDATE users SET referral_bonuses_available = referral_bonuses_available - 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
        return True


# ─── Spreads helpers ──────────────────────────────────────────────────────────

async def save_spread(
    user_id: int,
    spread_type: str,
    question: Optional[str],
    response: str,
    summary: Optional[str] = None,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO spreads (user_id, spread_type, question, response, summary)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, spread_type, question, response, summary),
        )
        await db.commit()
        return cursor.lastrowid


async def get_spread_by_id(spread_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM spreads WHERE id = ?", (spread_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_recent_spreads(user_id: int, limit: int = 3) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM spreads WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_spreads_last_7_days(user_id: int) -> list[dict]:
    since = (datetime.utcnow() - timedelta(days=7)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM spreads WHERE user_id = ? AND created_at >= ? ORDER BY created_at",
            (user_id, since),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ─── Reminder helpers ─────────────────────────────────────────────────────────

async def get_inactive_users(days: int = 3) -> list[dict]:
    threshold = (datetime.utcnow() - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM users
            WHERE (last_active IS NULL OR last_active <= ?)
            AND created_at <= datetime('now', '-1 day')
            """,
            (threshold,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_all_active_users() -> list[dict]:
    """Users who were active in the last 30 days."""
    threshold = (datetime.utcnow() - timedelta(days=30)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE last_active >= ?", (threshold,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_users_with_spreads_this_week() -> list[dict]:
    since = (datetime.utcnow() - timedelta(days=7)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT DISTINCT u.* FROM users u
            JOIN spreads s ON s.user_id = u.user_id
            WHERE s.created_at >= ?
            """,
            (since,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ─── Payment helpers ──────────────────────────────────────────────────────────

async def create_payment(
    user_id: int,
    amount,
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
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


# ─── Velhar state & AI question counter ──────────────────────────────────────

async def increment_ai_question_count(user_id: int) -> int:
    """Increment and return the new ai_question_count."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET ai_question_count = ai_question_count + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
        async with db.execute(
            "SELECT ai_question_count FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 1


async def set_velhar_state(user_id: int, state: str):
    """Set velhar_state: 'calm' or 'cold'."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET velhar_state = ? WHERE user_id = ?",
            (state, user_id),
        )
        await db.commit()


async def reset_velhar_state(user_id: int):
    """Reset to calm state and clear AI question counter."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET velhar_state = 'calm', ai_question_count = 0 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def increment_spreads_since_memory(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET spreads_since_memory = spreads_since_memory + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def reset_spreads_since_memory(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET spreads_since_memory = 0 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


# ─── Stats ────────────────────────────────────────────────────────────────────

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
