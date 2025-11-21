import os
import asyncio
import sqlite3
import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command


# ---------------- CONFIG ----------------
TOKEN = os.environ.get("TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()


# ---------------- DATABASE ----------------
conn = sqlite3.connect("searches.db")
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS searches(
        user_id INTEGER,
        url TEXT,
        name TEXT
    )
""")
conn.commit()


# ---------------- PARSER ----------------
async def fetch_new_items(session, url, user_id) -> list:
    return []   # заглушка


# ---------------- BACKGROUND MONITOR ----------------
async def monitor():
    await asyncio.sleep(5)

    while True:
        async with aiohttp.ClientSession() as session:
            c.execute("SELECT DISTINCT user_id FROM searches")
            users = c.fetchall()

            for (user_id,) in users:
                c.execute("SELECT url, name FROM searches WHERE user_id=?", (user_id,))
                tasks = c.fetchall()

                for url, name in tasks:
                    items = await fetch_new_items(session, url, user_id)

                    for item in items:
                        msg = (
                            f"<b>{item['title']}</b>\n"
                            f"Цена: {item['price']}\n"
                            f"{item['url']}"
                        )
                        await bot.send_message(user_id, msg)

        await asyncio.sleep(30)


# ---------------- HANDLERS ----------------
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    await msg.answer("Бот запущен и работает через вебхук 🚀")


# ---------------- WEBHOOK ----------------
async def handle_webhook(request):
    data = await request.json()
    update = types.Update.model_validate(data)
    await dp.dispatch(update, bot)
    return web.Response(text="OK")


async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)

    asyncio.create_task(monitor())

    print("Webhook установлен:", WEBHOOK_URL)


async def on_shutdown(app):
    await bot.session.close()


# ---------------- APP SERVER ----------------
def setup_app():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


app = setup_app()
