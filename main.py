import os
import re
import requests
import xml.etree.ElementTree as ET

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
if not CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID is not set")

RSS_URL = "http://apod.nasa.gov/apod.rss"


def get_apod_from_rss():
    """Возвращает словарь с данными APOD из RSS."""
    resp = requests.get(RSS_URL, timeout=20)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("RSS channel not found")

    item = channel.find("item")
    if item is None:
        raise RuntimeError("RSS item not found")

    title = item.findtext("title", default="NASA APOD")
    link = item.findtext("link", default="")

    desc_raw = item.findtext("description", default="")
    # вырезаем HTML-теги из описания
    description = re.sub(r"<.*?>", "", desc_raw).strip()

    enclosure = item.find("enclosure")
    image_url = None
    if enclosure is not None:
        image_url = enclosure.attrib.get("url")

    return {
        "title": title,
        "link": link,
        "description": description,
        "image_url": image_url,
    }


def build_caption(data):
    title = data["title"]
    description = data["description"]

    caption = f"{title}\n\n{description}"
    if len(caption) > 1000:
        caption = caption[:1000] + "..."
    return caption


def send_photo(image_url, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": image_url,
        "caption": caption,
    }
    r = requests.post(url, data=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
    }
    r = requests.post(url, data=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def main():
    data = get_apod_from_rss()
    caption = build_caption(data)

    if data["image_url"]:
        # есть прямая ссылка на картинку
        send_photo(data["image_url"], caption)
    else:
        # картинку не нашли – шлём просто текст и ссылку
        text = f"{caption}\n\n{data['link']}"
        send_message(text)


if __name__ == "__main__":
    main()
