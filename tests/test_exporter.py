"""Unit tests for scraper.exporter module."""

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scraper.parser import Book
from scraper.exporter import export_csv, export_json, ExportError, _build_filepath


def _sample_books() -> list[Book]:
    return [
        Book(
            title="A Light in the Attic",
            price=51.77,
            rating=3,
            availability=True,
            category="Poetry",
            url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        ),
        Book(
            title="Tipping the Velvet",
            price=53.74,
            rating=1,
            availability=False,
            category="Historical Fiction",
            url="https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
        ),
    ]


class TestBuildFilepath(unittest.TestCase):

    @patch("scraper.exporter.date")
    def test_filename_format(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = _build_filepath(Path(tmp), "csv")
            self.assertEqual(path.name, "books_2026-02-06.csv")

    @patch("scraper.exporter.date")
    def test_creates_directory(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp) / "deep" / "nested"
            _build_filepath(nested, "json")
            self.assertTrue(nested.exists())


class TestExportCsv(unittest.TestCase):

    @patch("scraper.exporter.date")
    def test_creates_csv_file(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_csv(_sample_books(), Path(tmp))
            self.assertTrue(path.exists())
            self.assertEqual(path.suffix, ".csv")

    @patch("scraper.exporter.date")
    def test_csv_has_header_and_rows(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_csv(_sample_books(), Path(tmp))
            with open(path, encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["title"], "A Light in the Attic")
            self.assertEqual(rows[0]["price"], "51.77")
            self.assertEqual(rows[0]["availability"], "True")

    @patch("scraper.exporter.date")
    def test_csv_column_order(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_csv(_sample_books(), Path(tmp))
            with open(path, encoding="utf-8") as fh:
                header = next(csv.reader(fh))
            expected = ["title", "price", "rating", "availability", "category", "url"]
            self.assertEqual(header, expected)

    @patch("scraper.exporter.date")
    def test_csv_empty_list(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_csv([], Path(tmp))
            with open(path, encoding="utf-8") as fh:
                rows = list(csv.reader(fh))
            self.assertEqual(len(rows), 1)  # header only

    @patch("scraper.exporter.date")
    def test_csv_returns_path(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_csv(_sample_books(), Path(tmp))
            self.assertIsInstance(path, Path)
            self.assertEqual(path.name, "books_2026-02-06.csv")

    @patch("scraper.exporter.date")
    def test_csv_string_output_dir(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_csv(_sample_books(), tmp)  # str, not Path
            self.assertTrue(path.exists())


class TestExportJson(unittest.TestCase):

    @patch("scraper.exporter.date")
    def test_creates_json_file(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_json(_sample_books(), Path(tmp))
            self.assertTrue(path.exists())
            self.assertEqual(path.suffix, ".json")

    @patch("scraper.exporter.date")
    def test_json_structure(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_json(_sample_books(), Path(tmp))
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["title"], "A Light in the Attic")
            self.assertAlmostEqual(data[0]["price"], 51.77)
            self.assertEqual(data[0]["rating"], 3)
            self.assertIs(data[0]["availability"], True)

    @patch("scraper.exporter.date")
    def test_json_empty_list(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_json([], Path(tmp))
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data, [])

    @patch("scraper.exporter.date")
    def test_json_preserves_types(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_json(_sample_books(), Path(tmp))
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            book = data[1]
            self.assertIsInstance(book["price"], float)
            self.assertIsInstance(book["rating"], int)
            self.assertIsInstance(book["availability"], bool)

    @patch("scraper.exporter.date")
    def test_json_trailing_newline(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_json(_sample_books(), Path(tmp))
            raw = path.read_text(encoding="utf-8")
            self.assertTrue(raw.endswith("\n"))

    @patch("scraper.exporter.date")
    def test_json_returns_path(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 6)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with tempfile.TemporaryDirectory() as tmp:
            path = export_json(_sample_books(), Path(tmp))
            self.assertEqual(path.name, "books_2026-02-06.json")


class TestExportError(unittest.TestCase):

    def test_attributes(self):
        err = ExportError(Path("output/test.csv"), "Permission denied")
        self.assertEqual(err.path, Path("output/test.csv"))
        self.assertEqual(err.reason, "Permission denied")
        self.assertIn("Permission denied", str(err))


if __name__ == "__main__":
    unittest.main()
