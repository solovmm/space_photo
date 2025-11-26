import os
import requests

NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def get_apod():
    url = "https://api.nasa.gov/planetary/apod"
    params = {
        "api_key": NASA_API_KEY,
        "thumbs": "true",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def build_caption(data):
    title = data.get("title", "NASA APOD")
    date = data.get("date", "")
    explanation = data.get("explanation", "")

    caption = f"{title}\n{date}\n\n{explanation}"

    # Ограничение Telegram на подпись к фото около 1024 символов
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
    data = get_apod()
    media_type = data.get("media_type")
    image_url = data.get("hdurl") or data.get("url")
    caption = build_caption(data)

    if media_type == "image" and image_url:
        send_photo(image_url, caption)
    else:
        # На случай если это видео или что то еще
        url = data.get("url", "")
        text = f"NASA APOD (не картинка)\n\n{caption}\n\n{url}"
        send_message(text)


if __name__ == "__main__":
    main()
