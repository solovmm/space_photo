import os
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
if not CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID is not set")

APOD_API_URL = "https://api.nasa.gov/planetary/apod"
APOD_PAGE_URL = "https://apod.nasa.gov/apod/astropix.html"


def get_apod():
    """Берем данные APOD с NASA API: заголовок и HD-картинку."""
    params = {"api_key": NASA_API_KEY}
    resp = requests.get(APOD_API_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    title = data.get("title", "NASA APOD")
    image_url = data.get("hdurl") or data.get("url")

    return {
        "title": title,
        "image_url": image_url,
        # ссылка на страницу APOD, как на сайте
        "link": APOD_PAGE_URL,
    }


def build_caption(info):
    title = info["title"]
    link = info["link"]

    # Заголовок + пустая строка + ссылка
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
    image_url = info["image_url"]

    if image_url:
        try:
            send_photo(image_url, caption)
        except requests.HTTPError:
            # если вдруг фото не отправилось (слишком большое и т.п.) - шлем только текст
            send_message(caption)
    else:
        send_message(caption)


if __name__ == "__main__":
    main()
