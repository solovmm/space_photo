import os
import re
import html
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
if not CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID is not set")

# Страница тега "image-of-the-day"
SPACE_TAG_URL = "https://www.space.com/tag/image-of-the-day"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; space-photo-bot/1.0; +https://www.space.com/)"
}


def get_space_photo_of_the_day():
    """
    1) Берём страницу https://www.space.com/tag/image-of-the-day
    2) Ищем ссылку на свежую статью:
       - сначала href с 'space-photo-of-the-day'
       - если нет, то href с 'image-of-the-day', но НЕ /tag/...
    3) Открываем статью, берём заголовок и большую картинку (og:image)
    """
    # Страница тега
    resp = requests.get(SPACE_TAG_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html_tag = resp.text

    # --- 1. Ищем ссылку со строкой 'space-photo-of-the-day' (URL статьи) ---
    m = re.search(
        r'href=["\']([^"\']*space-photo-of-the-day[^"\']*)["\']',
        html_tag,
        flags=re.IGNORECASE,
    )

    # --- 2. Если не нашли, ищем 'image-of-the-day', но исключаем /tag/... ---
    if not m:
        m = re.search(
            r'href=["\'](/(?!tag/)[^"\']*image-of-the-day[^"\']*)["\']',
            html_tag,
            flags=re.IGNORECASE,
        )

    if not m:
        raise RuntimeError("Не удалось найти ссылку на статью Image of the Day")

    article_path = m.group(1)

    if article_path.startswith("http"):
        article_url = article_path
    else:
        article_url = "https://www.space.com" + article_path

    print("Article URL:", article_url)

    # --- Страница статьи ---
    resp2 = requests.get(article_url, headers=HEADERS, timeout=30)
    resp2.raise_for_status()
    html_article = resp2.text

    # Заголовок: сначала og:title
    m_title = re.search(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        html_article,
        flags=re.IGNORECASE,
    )
    if m_title:
        title = html.unescape(m_title.group(1)).strip()
    else:
        # fallback: <h1>...</h1>
        m_h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html_article, flags=re.DOTALL | re.IGNORECASE)
        if m_h1:
            title_raw = re.sub(r"<.*?>", "", m_h1.group(1))
            title = html.unescape(title_raw).strip()
        else:
            title = "Space Image of the Day"

    # Картинка: og:image
    m_img = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html_article,
        flags=re.IGNORECASE,
    )
    image_url = None
    if m_img:
        image_url = m_img.group(1).strip()
    else:
        # fallback: первая <img> на странице
        m_img2 = re.search(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            html_article,
            flags=re.IGNORECASE,
        )
        if m_img2:
            image_url = m_img2.group(1).strip()

    return {
        "title": title,
        "link": article_url,
        "image_url": image_url,
    }


def build_caption(data):
    """
    Подпись: только первая часть заголовка (до ' | ') + ссылка.
    """
    raw_title = data["title"] or ""
    # режем всё, что идёт после " | "
    title = raw_title.split(" | ")[0].strip()
    link = data["link"]

    caption = f"{title}\n\n{link}"
    if len(caption) > 1000:
        caption = caption[:1000]
    return caption


def send_photo(image_url, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": image_url,
        "caption": caption,
    }
    r = requests.post(url, data=payload, timeout=30)
    if not r.ok:
        print("Telegram sendPhoto error:", r.status_code, r.text)
    r.raise_for_status()
    return r.json()


def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
    }
    r = requests.post(url, data=payload, timeout=30)
    if not r.ok:
        print("Telegram sendMessage error:", r.status_code, r.text)
    r.raise_for_status()
    return r.json()


def main():
    data = get_space_photo_of_the_day()
    caption = build_caption(data)
    image_url = data.get("image_url")

    if image_url:
        try:
            send_photo(image_url, caption)
            return
        except requests.HTTPError:
            print("Ошибка при отправке фото, шлём только текст...")

    # если нет картинки или не получилось отправить
    send_message(caption)


if __name__ == "__main__":
    main()
