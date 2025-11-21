import os
import re
import asyncio
import hashlib
import sqlite3
import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + "/webhook"

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)


# ---------------- DATABASE ----------------
conn = sqlite3.connect('avito.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS searches (user_id INTEGER, url TEXT, name TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS seen (user_id INTEGER, item_id TEXT)''')
conn.commit()


def get_id(url):
    return hashlib.md5(url.encode()).hexdigest()


# ---------------- PARSING ----------------
async def fetch_new_items(session, url, user_id):
    mobile_url = url.replace("www.avito.ru", "m.avito.ru")
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"}

    try:
        async with session.get(mobile_url, headers=headers, timeout=20) as resp:
            text = await resp.text()

        links = re.findall(r'href="(/[^"]+item[^"]*)"', text)[:10]
        new = []

        for link in links:
            full_url = "https://www.avito.ru" + link.split('?')[0]
            item_id = get_id(full_url)

            c.execute("SELECT 1 FROM seen WHERE user_id=? AND item_id=?", (user_id, item_id))
            if not c.fetchone():
                c.execute("INSERT INTO seen VALUES (?, ?)", (user_id, item_id))
                conn.commit()

                async with session.get(full_url, headers=headers) as r:
                    itext = await r.text()

                title = re.search(r'<h1[^>]*>([^<]+)</h1>', itext)
                price = re.search(r'class="price[^>]*"[^>]*>([^<]+)', itext)
                photo = re.search(r'"imageUrl":"([^"]+)"', itext)

                new.append({
                    "title": title.group(1) if title else "Без названия",
                    "price": price.group(1).strip() if price else "Цена не указана",
                    "url": full_url,
                    "photo": photo.group(1) if photo else None
                })

        return new

    except Exception as e:
        print("ERROR:", e)
        return []


# ---------------- BACKGROUND MONITOR ----------------
async def monitor():
    await asyncio.sleep(3)
    while True:
        async with aiohttp.ClientSession() as session:
            c.execute("SELECT DISTINCT user_id FROM searches")
            users = c.fetchall()

            for (user_id,) in users:
                c.execute("SELECT url, name FROM searches WHERE user_id=?", (user_id,))
                for url, name in c.fetchall():
                    items = await fetch_new_items(session, url, user_id)
                    for item in items:
                        msg = f"<b>{item['title']}</b>\nЦена: {item['price']}\n{item['url']}"
                        await bot.send_message(user_id, msg)

        await asyncio.sleep(30)


# ---------------- HANDLERS ----------------
@dp.message_handler(commands=['start'])
async def start_cmd(msg: types.Message):
    await msg.answer("Бот работает через вебхук 🎯")


# ---------------- WEBHOOK ----------------
async def handle_webhook(request):
    data = await request.json()
    update = types.Update.to_object(data)
    await dp.process_update(update)
    return web.Response()


async def on_startup(app):
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(monitor())


async def on_shutdown(app):
    await bot.session.close()


# ---------------- APP SERVER ----------------
def setup_app():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


if name == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    web.run_app(setup_app(), host="0.0.0.0", port=PORT)
