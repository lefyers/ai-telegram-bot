"""
Парсер centr-krasok.kz
Запускай вручную для обновления базы знаний: python scraper.py
"""

import requests
from bs4 import BeautifulSoup
import time
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}

BASE_URL = "https://centr-krasok.kz"

PAGES = [
    "/",
    "/about/",
    "/about/contacts/",
    "/catalog/",
]


def clean_text(text: str) -> str:
    """Убирает лишние пробелы и переносы строк."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_page(url: str) -> str:
    """Загружает страницу и извлекает полезный текст."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"  ОШИБКА при загрузке {url}: {e}")
        return ""

    soup = BeautifulSoup(r.text, "html.parser")

    # Удаляем скрипты, стили, навигацию, футер
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    # Берём основной контент
    main = (
        soup.find("main")
        or soup.find("div", class_=re.compile(r"content|main|article", re.I))
        or soup.body
    )

    if not main:
        return ""

    lines = []
    for el in main.find_all(["h1", "h2", "h3", "p", "li", "td", "th", "span"]):
        txt = clean_text(el.get_text())
        if len(txt) > 20:  # фильтруем короткий мусор
            lines.append(txt)

    # Дедупликация подряд идущих одинаковых строк
    result = []
    prev = ""
    for line in lines:
        if line != prev:
            result.append(line)
            prev = line

    return "\n".join(result)


def scrape_all() -> str:
    sections = []
    for path in PAGES:
        url = BASE_URL + path
        print(f"Парсю: {url}")
        content = parse_page(url)
        if content:
            sections.append(f"=== {url} ===\n{content}\n")
        time.sleep(1)  # пауза между запросами

    return "\n".join(sections)


if __name__ == "__main__":
    print("Начинаю парсинг centr-krasok.kz...\n")
    data = scrape_all()

    out_path = "company_info_raw.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(data)

    print(f"\nГотово! Сырые данные сохранены в {out_path}")
    print(f"Размер: {len(data):,} символов")
    print("\nПросмотри файл, отредактируй при необходимости,")
    print("затем замени содержимое company_info.txt.")
