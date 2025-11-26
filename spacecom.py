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

SPACE_HOME_URL = "https://www.space.com/"

HEADERS = {
    # Просто нормальный User-Agent, чтобы сайт не резал бота
    "User-Agent": "Mozilla/5.0 (compatible; space-photo-bot/1.0; +https://www.space.com/)"
}


def get_space_photo_of_the_day():
    """
    1) Берём главную страницу space.com
    2) Находим ссылку на 'Space photo of the day'
    3) Открываем статью, берём заголовок и большую картинку (og:image)
    """
    # Главная страница
    resp = requests.get(SPACE_HOME_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html_home = resp.text

    # --- 1. Пытаемся найти <a ...>...</a>, внутри которого есть 'Space photo of the day' ---
    pattern = re.compile(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>.*?Space photo of the day.*?</a>',
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(html_home)

    # --- 2. Если не нашли — fallback: ищем текст и откатываемся назад до ближайшего <a ... href="..."> ---
    if not m:
        lower = html_home.lower()
        idx = lower.find("space photo of the day")
        if idx == -1:
            raise RuntimeError("Не удалось найти текст 'Space photo of the day' на главной странице")

        # ищем начало <a ...> перед этим текстом
        start_a = lower.rfind("<a", 0, idx)
        if start_a == -1:
            raise RuntimeError("Не удалось найти <a ...> перед 'Space photo of the day'")

        snippet = html_home[start_a:idx]
        m_href = re.search(r'href=["\']([^"\']+)["\']', snippet, re.IGNORECASE)
        if not m_href:
            raise RuntimeError("Не удалось вытащить href для 'Space photo of the day'")

        article_path = m_href.group(1)
    else:
        article_path = m.group(1)

    if article_path.startswith("http"):
        article_url = article_path
    else:
        article_url = "https://www.space.com" + article_path

    # --- Страница статьи ---
    resp2 = requests.get(article_url, headers=HEADERS, timeout=30)
    resp2.raise_for_status()
    html_article = resp2.text

    # Заголовок: сначала пробуем og:title
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
            title = "Space Photo of the Day"

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
        # fallback: первая картинка на странице
        m_img2 = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_article, flags=re.IGNORECASE)
        if m_img2:
            image_url = m_img2.group(1).strip()

    return {
        "title": title,
        "link": article_url,
        "image_url": image_url,
    }


def build_caption(data):
    """
    Подпись: заголовок + пустая строка + ссылка на статью.
    """
    title = data["title"]
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
