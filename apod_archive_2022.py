import os
import json
import requests
from datetime import datetime, timezone, date

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
if not CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID is not set")

ARCHIVE_FILE = "apod_2022_offline.json"


def load_archive():
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # сортируем по дате, чтобы шли как в году
    data_sorted = sorted(data, key=lambda x: x["date"])
    return data_sorted


def pick_item_deterministic(archive):
    """
    Выбираем элемент БЕЗ случайности:
    - считаем номер дня с базовой даты,
    - определяем слот в зависимости от часа (UTC),
    - считаем индекс по формуле (day_index * 3 + slot) % N.
    """
    if not archive:
        raise RuntimeError("Архив пустой или не найден")

    n = len(archive)

    now = datetime.now(timezone.utc)
    # базовая дата — настроим, с какого дня начать цикл
    base_date = date(2025, 1, 1)
    day_index = (now.date() - base_date).days
    if day_index < 0:
        day_index = 0

    # определяем, какой слот запуска (по UTC-часу)
    hour = now.hour
    # твой cron: 0 6, 0 11, 0 18 → 3 слота
    if hour == 6:
        slot = 0
    elif hour == 11:
        slot = 1
    elif hour == 18:
        slot = 2
    else:
        # если вдруг руками запустил в другое время — считаем нулевой слот
        slot = 0

    run_index = (day_index * 3 + slot) % n
    item = archive[run_index]
    print(f"Selected index: {run_index} of {n}, date={item.get('date')}")
    return item


def build_caption(item):
    """
    Подпись как у обычного APOD: заголовок + ссылка на страницу.
    Без признаков 'архива'.
    """
    title = item["title"]
    link = item["page_url"]
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
    archive = load_archive()
    item = pick_item_deterministic(archive)

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
