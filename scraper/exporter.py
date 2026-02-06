"""Export scraped book data to CSV and JSON files.

Usage::

    from scraper.parser import Book
    from scraper.exporter import export_csv, export_json
    from pathlib import Path

    books: list[Book] = [...]
    path = export_csv(books, Path("output"))
    path = export_json(books, Path("output"))
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, fields
from datetime import date
from pathlib import Path

from scraper.parser import Book

__all__ = ["export_csv", "export_json", "ExportError"]

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Raised when export to file fails."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Export failed for {path}: {reason}")


def _build_filepath(output_dir: Path, extension: str) -> Path:
    """Build output file path with today's date.

    Creates *output_dir* if it does not exist.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"books_{date.today().isoformat()}.{extension}"
    return output_dir / filename


def export_csv(
    books: list[Book],
    output_dir: Path | str = Path("output"),
) -> Path:
    """Export books to a CSV file named ``books_YYYY-MM-DD.csv``.

    Returns:
        Path to the written file.

    Raises:
        ExportError: On I/O failure.
    """
    output_dir = Path(output_dir)
    filepath = _build_filepath(output_dir, "csv")
    fieldnames = [f.name for f in fields(Book)]

    try:
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for book in books:
                writer.writerow(asdict(book))
    except OSError as exc:
        raise ExportError(filepath, str(exc)) from exc

    logger.info("Exported %d books to %s", len(books), filepath)
    return filepath


def export_json(
    books: list[Book],
    output_dir: Path | str = Path("output"),
) -> Path:
    """Export books to a JSON file named ``books_YYYY-MM-DD.json``.

    Returns:
        Path to the written file.

    Raises:
        ExportError: On I/O failure.
    """
    output_dir = Path(output_dir)
    filepath = _build_filepath(output_dir, "json")
    data = [asdict(book) for book in books]

    try:
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    except OSError as exc:
        raise ExportError(filepath, str(exc)) from exc

    logger.info("Exported %d books to %s", len(books), filepath)
    return filepath
