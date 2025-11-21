import asyncio
import aiohttp
import hashlib
import sqlite3
import re
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.environ.get('TOKEN')
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

conn = sqlite3.connect('avito.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS searches (user_id INTEGER, url TEXT, name TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS seen (user_id INTEGER, item_id TEXT)''')
conn.commit()

def get_id(url): return hashlib.md5(url.encode()).hexdigest()

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
           c.execute("SELECT 1 FROM seen WHERE user_id=? AND item_id=?", "(user_id, item_id))
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
    except:
        return []

async def monitor():
    while True:
        async with aiohttp.ClientSession() as session:
            c.execute("SELECT DISTINCT user_id FROM searches")
            for (user_id,) in c.fetchall():
                c.execute("SELECT url, name FROM searches WHERE user_id=?", (user_id,))
