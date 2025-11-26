import os
import requests

# Переменные окружения из GitHub Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")  # если секрета нет, используем DEMO_KEY

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
if not CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID is not set")

APOD_API_URL = "https://api.nasa.gov/planetary/apod"
APOD_PAGE_BASE = "https://apod.nasa.gov/apod"


def build_apod_page_url(date_str: str | None) -> str:
    """
    Строим персональную ссылку на страницу APOD вида:
    https://apod.nasa.gov/apod/apYYMMDD.html

    Если даты нет или формат странный – падаем обратно на astropix.html.
    """
    if not date_str:
        return f"{APOD_PAGE_BASE}/astropix.html"

    try:
        year, month, day = date_str.split("-")  # "2025-11-26"
        yy = year[2:]                            # "25"
        return f"{APOD_PAGE_BASE}/ap{yy}{month}{day}.html"
    except Exception:
        return f"{APOD_PAGE_BASE}/astropix.html"


def get_apod():
    """Берем данные APOD с NASA API: заголовок и ссылки на картинку."""
    params = {"api_key": NASA_API_KEY}
    resp = requests.get(APOD_API_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    title = data.get("title", "NASA APOD")
    media_type = data.get("media_type", "image")
    date_str = data.get("date")  # "2025-11-26"

    hd_image_url = None
    image_url = None

    if media_type == "image":
        hd_image_url = data.get("hdurl")
        image_url = data.get("url")

    page_url = build_apod_page_url(date_str)

    return {
        "title": title,
        "date": date_str,
        "hd_image_url": hd_image_url,
        "image_url": image_url,
        "media_type": media_type,
        # персональная страница APOD на сайте
        "link": page_url,
        # на всякий случай сохраним сырой url из API (для видео и т.п.)
        "raw_url": data.get("url"),
    }


def build_caption(info):
    """Подпись: название + пустая строка + персональная ссылка на APOD."""
    title = info["title"]
    link = info["link"]

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
    info = get_apod()
    caption = build_caption(info)
    media_type = info.get("media_type", "image")

    # Если это не картинка (например, видео) — шлем текст + raw_url
    if media_type != "image":
        extra = info.get("raw_url") or ""
        text = caption if not extra else f"{caption}\n\n{extra}"
        send_message(text)
        return

    hd_url = info.get("hd_image_url")
    normal_url = info.get("image_url")

    # 1. Пытаемся отправить HD-версию
    if hd_url:
        try:
            send_photo(hd_url, caption)
            return
        except requests.HTTPError:
            print("HD image failed, trying normal URL...")

    # 2. Если HD не получилось или её нет – пробуем обычную картинку
    if normal_url:
        try:
            send_photo(normal_url, caption)
            return
        except requests.HTTPError:
            print("Normal image failed, sending text only...")

    # 3. Совсем без картинок – отправляем просто текст
    send_message(caption)


if __name__ == "__main__":
    main()
