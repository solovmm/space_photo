import os
import json
import random
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
if not CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID is not set")

ARCHIVE_FILE = "apod_2022_offline.json"


def load_archive():
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_caption(item):
    title = item["title"]
    link = item["page_url"]
    caption = f"NASA APOD (архив 2022): {title}\n\n{link}"
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
    archive = load_archive()
    if not archive:
        raise RuntimeError("Архив пустой или не найден")

    item = random.choice(archive)
    caption = build_caption(item)
    image_url = item.get("image_url")

    if image_url:
        try:
            send_photo(image_url, caption)
            return
        except requests.HTTPError:
            print("Не удалось отправить фото, шлём только текст...")

    # если нет картинки или ошибка при отправке
    send_message(caption)


if __name__ == "__main__":
    main()
