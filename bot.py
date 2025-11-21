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

            # Проверяем, видели ли мы уже этот товар
            c.execute(
                "SELECT 1 FROM seen WHERE user_id=? AND item_id=?",
                (user_id, item_id)
            )

            if not c.fetchone():
                # Записываем, что теперь увидели
                c.execute(
                    "INSERT INTO seen VALUES (?, ?)",
                    (user_id, item_id)
                )
                conn.commit()

                # Загружаем страницу товара
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
        print("Error:", e)
        return []
