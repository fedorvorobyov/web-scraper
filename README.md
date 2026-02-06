# Web Scraper

CLI-инструмент для парсинга книг с [books.toscrape.com](https://books.toscrape.com/) — легального тренировочного сайта для веб-скрапинга.

Собирает название, цену, рейтинг, наличие, категорию и URL каждой книги. Экспортирует в CSV или JSON.

## Quick Start

```bash
git clone https://github.com/user/web-scraper.git
cd web-scraper
pip install -r requirements.txt

# Парсить первые 5 страниц каталога
python -m scraper.main --pages 5 --format csv

# Парсить весь каталог (50 страниц, ~1000 книг)
python -m scraper.main --all --format json

# Парсить конкретную категорию
python -m scraper.main --category "Science" --format csv
```

## Пример вывода

```
[INFO] Starting scraper...
[INFO] Fetcher initialized (max_retries=3, backoff=1.0, delay=1.0s, timeout=10s)
[INFO] OK https://books.toscrape.com/catalogue/page-1.html (0.34s)
[INFO] Parsed 20 books from https://books.toscrape.com/catalogue/page-1.html
[INFO] Page 1 - 20 books found (total: 20)
...
[INFO] Done! 100 books scraped in 12.3s
[INFO] Saved to output/books_2026-02-06.csv

Summary:
  Total books: 100
  Avg price: £35.42
  Rating distribution: 5★ 18 | 4★ 23 | 3★ 31 | 2★ 19 | 1★ 9
```

## CLI-опции

| Флаг | Описание |
|------|----------|
| `--pages N` | Парсить первые N страниц каталога |
| `--all` | Парсить весь каталог |
| `--category NAME` | Парсить конкретную категорию (регистронезависимо) |
| `--format csv\|json` | Формат экспорта (по умолчанию: csv) |
| `--output-dir DIR` | Директория для результатов (по умолчанию: output) |

Режимы `--pages`, `--all` и `--category` взаимоисключающие — нужно выбрать один.

## Архитектура

```
scraper/
├── fetcher.py    HTTP-клиент с retry и rate limiting
├── parser.py     Парсинг HTML → dataclass Book
├── exporter.py   Сериализация в CSV / JSON
└── main.py       CLI, оркестрация, статистика
```

**Fetcher** — `requests.Session` с переиспользованием TCP-соединений (keep-alive). Retry с exponential backoff (1s → 2s → 4s) на ошибки 429/5xx, ConnectionError и Timeout. Управляемая задержка между запросами (rate limiting). Не ретраит 404 и другие клиентские ошибки.

**Parser** — чистые функции парсинга (принимают HTML-строку, возвращают данные). `BooksParser` оркестратор связывает fetcher и парсинг, обходит пагинацию. Поддержка парсинга по категориям с case-insensitive поиском.

**Exporter** — `dataclasses.asdict` + `csv.DictWriter` / `json.dump`. Имя файла с датой (`books_2026-02-06.csv`). Автоматическое создание директории.

**Main** — `argparse` с mutually exclusive group, `logging` с форматом `[LEVEL] message`, `time.monotonic()` для замера времени, сводная статистика через `collections.Counter`.

## Тесты

```bash
python -m pytest tests/ -v
```

76 unit-тестов, все на `unittest.mock` — ни один не делает сетевых запросов.

| Модуль | Тестов | Что покрыто |
|--------|--------|-------------|
| fetcher | 10 | success, retry на 500, 404 без retry, все retry исчерпаны, rate limiting, backoff delays, ConnectionError, Timeout, request_count, context manager |
| parser | 28 | catalog page (title, price, rating, availability, URL, category, empty, out of stock), pagination, categories, book detail, breadcrumb, BooksParser orchestration |
| exporter | 15 | CSV/JSON создание, заголовки, типы данных, пустой список, trailing newline, строковый путь, ExportError |
| main | 23 | argparse (все режимы, валидация, mutual exclusion), print_summary, orchestration happy path, FetchError/ParseError/ExportError handling, edge cases |

## Зависимости

- **requests** — HTTP-клиент
- **beautifulsoup4** + **lxml** — парсинг HTML
- **Python 3.10+** — для `X | Y` type union syntax

Все остальное — стандартная библиотека: `argparse`, `csv`, `json`, `logging`, `dataclasses`, `collections`, `pathlib`, `time`.

## Структура данных

Каждая книга представлена dataclass `Book`:

```python
@dataclass
class Book:
    title: str         # "A Light in the Attic"
    price: float       # 51.77
    rating: int        # 1-5
    availability: bool # True = in stock
    category: str      # "Poetry"
    url: str           # absolute URL to book page
```
