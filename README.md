# Web Scraper

CLI tool for scraping books from [books.toscrape.com](https://books.toscrape.com/) — a legitimate practice website for web scraping.

Collects title, price, rating, availability, category, and URL for each book. Exports to CSV or JSON.

## Quick Start

```bash
git clone https://github.com/fedorvorobyov/web-scraper.git
cd web-scraper
pip install -r requirements.txt

# Scrape first 5 pages of the catalog
python -m scraper.main --pages 5 --format csv

# Scrape the entire catalog (50 pages, ~1000 books)
python -m scraper.main --all --format json

# Scrape a specific category
python -m scraper.main --category "Science" --format csv
```

## Example Output

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

## CLI Options

| Flag | Description |
|------|-------------|
| `--pages N` | Scrape the first N pages of the catalog |
| `--all` | Scrape the entire catalog |
| `--category NAME` | Scrape a specific category (case-insensitive) |
| `--format csv\|json` | Export format (default: csv) |
| `--output-dir DIR` | Output directory (default: output) |

The `--pages`, `--all`, and `--category` modes are mutually exclusive — pick one.

## Architecture

```
scraper/
├── fetcher.py    HTTP client with retry and rate limiting
├── parser.py     HTML parsing → dataclass Book
├── exporter.py   Serialization to CSV / JSON
└── main.py       CLI, orchestration, statistics
```

**Fetcher** — `requests.Session` with TCP connection reuse (keep-alive). Retry with exponential backoff (1s → 2s → 4s) on 429/5xx errors, ConnectionError, and Timeout. Configurable delay between requests (rate limiting). Does not retry 404 and other client errors.

**Parser** — Pure parsing functions (accept HTML string, return data). `BooksParser` orchestrator connects the fetcher and parsing, handles pagination. Supports category parsing with case-insensitive search.

**Exporter** — `dataclasses.asdict` + `csv.DictWriter` / `json.dump`. Date-stamped filenames (`books_2026-02-06.csv`). Automatic directory creation.

**Main** — `argparse` with mutually exclusive group, `logging` with `[LEVEL] message` format, `time.monotonic()` for timing, summary statistics via `collections.Counter`.

## Tests

```bash
python -m pytest tests/ -v
```

76 unit tests, all using `unittest.mock` — none make network requests.

| Module | Tests | Coverage |
|--------|-------|----------|
| fetcher | 10 | success, retry on 500, no retry on 404, all retries exhausted, rate limiting, backoff delays, ConnectionError, Timeout, request_count, context manager |
| parser | 28 | catalog page (title, price, rating, availability, URL, category, empty, out of stock), pagination, categories, book detail, breadcrumb, BooksParser orchestration |
| exporter | 15 | CSV/JSON creation, headers, data types, empty list, trailing newline, string path, ExportError |
| main | 23 | argparse (all modes, validation, mutual exclusion), print_summary, orchestration happy path, FetchError/ParseError/ExportError handling, edge cases |

## Dependencies

- **requests** — HTTP client
- **beautifulsoup4** + **lxml** — HTML parsing
- **Python 3.10+** — for `X | Y` type union syntax

Everything else is standard library: `argparse`, `csv`, `json`, `logging`, `dataclasses`, `collections`, `pathlib`, `time`.

## Data Model

Each book is represented as a `Book` dataclass:

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

## License

MIT
