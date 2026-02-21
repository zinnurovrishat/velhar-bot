import asyncio
import json
import logging
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

from config import config
from database import init_db
from handlers import start, spreads, payment, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def create_bot_and_dp() -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers (order matters — more specific first)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(spreads.router)

    return bot, dp


# ─── Polling mode (local dev / testing) ──────────────────────────────────────

async def run_polling():
    await init_db()
    bot, dp = await create_bot_and_dp()
    logger.info("Starting VELHAR bot in polling mode...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


# ─── Webhook mode (production VPS) ───────────────────────────────────────────

async def run_webhook():
    await init_db()
    bot, dp = await create_bot_and_dp()

    webhook_path = f"/webhook/{config.bot_token}"
    webhook_url = config.webhook_url.rstrip("/") + webhook_path

    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook set: {webhook_url}")

    app = web.Application()

    # ── Telegram updates ──────────────────────────────────────────────────────
    async def handle_telegram(request: web.Request) -> web.Response:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return web.Response()

    app.router.add_post(webhook_path, handle_telegram)

    # ── Health check ───────────────────────────────────────────────────────────
    async def health(_: web.Request) -> web.Response:
        return web.Response(text="VELHAR is alive")

    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Webhook server listening on :8080")

    try:
        await asyncio.Event().wait()  # run forever
    finally:
        await bot.delete_webhook()
        await runner.cleanup()
        await bot.session.close()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "polling"

    if mode == "webhook":
        asyncio.run(run_webhook())
    else:
        asyncio.run(run_polling())
