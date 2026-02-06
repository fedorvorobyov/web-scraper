"""CLI entry point for the books scraper.

Usage::

    python -m scraper.main --pages 5 --format csv
    python -m scraper.main --all --format json
    python -m scraper.main --category "Science" --format csv
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import Counter
from pathlib import Path

from scraper.fetcher import BooksFetcher, FetchError
from scraper.parser import Book, BooksParser, ParseError
from scraper.exporter import export_csv, export_json, ExportError

__all__ = ["build_parser", "print_summary", "main"]

logger = logging.getLogger(__name__)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with console output."""
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m scraper.main",
        description="Scrape books from books.toscrape.com",
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--pages", type=int, metavar="N",
        help="Scrape first N pages of the catalog",
    )
    mode.add_argument(
        "--all", action="store_true", default=False,
        help="Scrape the entire catalog",
    )
    mode.add_argument(
        "--category", type=str, metavar="NAME",
        help="Scrape a specific category by name",
    )

    parser.add_argument(
        "--format", choices=["csv", "json"], default="csv",
        help="Output format (default: csv)",
    )
    parser.add_argument(
        "--output-dir", type=str, default="output",
        help="Output directory (default: output)",
    )

    return parser


def print_summary(books: list[Book]) -> None:
    """Print summary statistics to stdout."""
    total = len(books)
    if total == 0:
        print("\nSummary:")
        print("  Total books: 0")
        return

    avg_price = sum(book.price for book in books) / total

    rating_counts = Counter(book.rating for book in books)
    distribution_parts = []
    for stars in (5, 4, 3, 2, 1):
        count = rating_counts.get(stars, 0)
        distribution_parts.append(f"{stars}\u2605 {count}")
    distribution = " | ".join(distribution_parts)

    print("\nSummary:")
    print(f"  Total books: {total}")
    print(f"  Avg price: \u00a3{avg_price:.2f}")
    print(f"  Rating distribution: {distribution}")


def main(argv: list[str] | None = None) -> None:
    """Run the scraper CLI."""
    args = build_parser().parse_args(argv)

    setup_logging()

    if args.pages is not None and args.pages < 1:
        logger.error("--pages must be >= 1, got %d", args.pages)
        sys.exit(1)

    export_fn = export_csv if args.format == "csv" else export_json

    logger.info("Starting scraper...")
    start_time = time.monotonic()

    try:
        with BooksFetcher() as fetcher:
            parser = BooksParser(fetcher)

            if args.category:
                books = parser.scrape_category(args.category)
            elif args.all:
                books = parser.scrape_catalog(max_pages=0)
            else:
                books = parser.scrape_catalog(max_pages=args.pages)

    except FetchError as exc:
        logger.error("Fetch failed: %s", exc)
        sys.exit(1)
    except ParseError as exc:
        logger.error("Parse failed: %s", exc)
        sys.exit(1)

    elapsed = time.monotonic() - start_time
    logger.info("Done! %d books scraped in %.1fs", len(books), elapsed)

    if not books:
        logger.warning("No books found. Nothing to export.")
        print_summary(books)
        return

    try:
        output_path = export_fn(books, args.output_dir)
    except ExportError as exc:
        logger.error("Export failed: %s", exc)
        sys.exit(1)

    logger.info("Saved to %s", output_path)
    print_summary(books)


if __name__ == "__main__":
    main()
