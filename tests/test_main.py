"""Unit tests for scraper.main module."""

import logging
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

from scraper.parser import Book
from scraper.main import build_parser, print_summary, main


def _sample_books() -> list[Book]:
    return [
        Book("Book A", 10.00, 5, True, "Science", "http://example.com/a"),
        Book("Book B", 20.00, 4, True, "Science", "http://example.com/b"),
        Book("Book C", 30.00, 3, False, "Fiction", "http://example.com/c"),
        Book("Book D", 40.00, 2, True, "Fiction", "http://example.com/d"),
        Book("Book E", 50.00, 1, True, "Travel", "http://example.com/e"),
    ]


class TestBuildParser(unittest.TestCase):

    def test_pages_mode(self):
        args = build_parser().parse_args(["--pages", "5", "--format", "csv"])
        self.assertEqual(args.pages, 5)
        self.assertFalse(args.all)
        self.assertIsNone(args.category)
        self.assertEqual(args.format, "csv")

    def test_all_mode(self):
        args = build_parser().parse_args(["--all", "--format", "json"])
        self.assertTrue(args.all)
        self.assertIsNone(args.pages)
        self.assertEqual(args.format, "json")

    def test_category_mode(self):
        args = build_parser().parse_args(["--category", "Science", "--format", "csv"])
        self.assertEqual(args.category, "Science")
        self.assertIsNone(args.pages)
        self.assertFalse(args.all)

    def test_default_format_is_csv(self):
        args = build_parser().parse_args(["--all"])
        self.assertEqual(args.format, "csv")

    def test_default_output_dir(self):
        args = build_parser().parse_args(["--all"])
        self.assertEqual(args.output_dir, "output")

    def test_custom_output_dir(self):
        args = build_parser().parse_args(["--all", "--output-dir", "results"])
        self.assertEqual(args.output_dir, "results")

    def test_mutually_exclusive_modes(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--pages", "5", "--all"])

    def test_no_mode_raises(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--format", "csv"])

    def test_invalid_format_rejected(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--all", "--format", "xml"])

    def test_pages_requires_int(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--pages", "abc"])


class TestPrintSummary(unittest.TestCase):

    @patch("sys.stdout", new_callable=StringIO)
    def test_summary_content(self, mock_stdout):
        print_summary(_sample_books())
        output = mock_stdout.getvalue()
        self.assertIn("Total books: 5", output)
        self.assertIn("Avg price: \u00a330.00", output)
        self.assertIn("5\u2605 1", output)
        self.assertIn("4\u2605 1", output)
        self.assertIn("3\u2605 1", output)
        self.assertIn("2\u2605 1", output)
        self.assertIn("1\u2605 1", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_summary_empty_list(self, mock_stdout):
        print_summary([])
        output = mock_stdout.getvalue()
        self.assertIn("Total books: 0", output)
        self.assertNotIn("Avg price", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_rating_order_descending(self, mock_stdout):
        print_summary(_sample_books())
        output = mock_stdout.getvalue()
        pos_5 = output.index("5\u2605")
        pos_1 = output.index("1\u2605")
        self.assertLess(pos_5, pos_1)

    @patch("sys.stdout", new_callable=StringIO)
    def test_missing_ratings_show_zero(self, mock_stdout):
        books = [Book("X", 10.0, 5, True, "Cat", "http://x.com")]
        print_summary(books)
        output = mock_stdout.getvalue()
        self.assertIn("4\u2605 0", output)
        self.assertIn("3\u2605 0", output)


class TestMain(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @patch("scraper.main.export_csv")
    @patch("scraper.main.BooksParser")
    @patch("scraper.main.BooksFetcher")
    def test_pages_mode_calls_scrape_catalog(
        self, mock_fetcher_cls, mock_parser_cls, mock_export
    ):
        mock_fetcher = MagicMock()
        mock_fetcher_cls.return_value.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_parser = mock_parser_cls.return_value
        mock_parser.scrape_catalog.return_value = _sample_books()
        mock_export.return_value = Path("output/books.csv")

        main(["--pages", "3", "--format", "csv"])
        mock_parser.scrape_catalog.assert_called_once_with(max_pages=3)
        mock_export.assert_called_once()

    @patch("scraper.main.export_json")
    @patch("scraper.main.BooksParser")
    @patch("scraper.main.BooksFetcher")
    def test_all_mode_calls_scrape_catalog_zero(
        self, mock_fetcher_cls, mock_parser_cls, mock_export
    ):
        mock_fetcher = MagicMock()
        mock_fetcher_cls.return_value.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_parser = mock_parser_cls.return_value
        mock_parser.scrape_catalog.return_value = _sample_books()
        mock_export.return_value = Path("output/books.json")

        main(["--all", "--format", "json"])
        mock_parser.scrape_catalog.assert_called_once_with(max_pages=0)

    @patch("scraper.main.export_csv")
    @patch("scraper.main.BooksParser")
    @patch("scraper.main.BooksFetcher")
    def test_category_mode(self, mock_fetcher_cls, mock_parser_cls, mock_export):
        mock_fetcher = MagicMock()
        mock_fetcher_cls.return_value.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_parser = mock_parser_cls.return_value
        mock_parser.scrape_category.return_value = _sample_books()
        mock_export.return_value = Path("output/books.csv")

        main(["--category", "Science", "--format", "csv"])
        mock_parser.scrape_category.assert_called_once_with("Science")

    @patch("scraper.main.BooksParser")
    @patch("scraper.main.BooksFetcher")
    def test_fetch_error_exits_1(self, mock_fetcher_cls, mock_parser_cls):
        mock_fetcher = MagicMock()
        mock_fetcher_cls.return_value.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher_cls.return_value.__exit__ = MagicMock(return_value=False)

        from scraper.fetcher import FetchError
        mock_parser = mock_parser_cls.return_value
        mock_parser.scrape_catalog.side_effect = FetchError("http://x.com", "fail")

        with self.assertRaises(SystemExit) as ctx:
            main(["--all"])
        self.assertEqual(ctx.exception.code, 1)

    @patch("scraper.main.BooksParser")
    @patch("scraper.main.BooksFetcher")
    def test_parse_error_exits_1(self, mock_fetcher_cls, mock_parser_cls):
        mock_fetcher = MagicMock()
        mock_fetcher_cls.return_value.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher_cls.return_value.__exit__ = MagicMock(return_value=False)

        from scraper.parser import ParseError
        mock_parser = mock_parser_cls.return_value
        mock_parser.scrape_category.side_effect = ParseError("http://x.com", "not found")

        with self.assertRaises(SystemExit) as ctx:
            main(["--category", "xyz"])
        self.assertEqual(ctx.exception.code, 1)

    @patch("scraper.main.export_csv")
    @patch("scraper.main.BooksParser")
    @patch("scraper.main.BooksFetcher")
    def test_export_error_exits_1(self, mock_fetcher_cls, mock_parser_cls, mock_export):
        mock_fetcher = MagicMock()
        mock_fetcher_cls.return_value.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_parser = mock_parser_cls.return_value
        mock_parser.scrape_catalog.return_value = _sample_books()

        from scraper.exporter import ExportError
        mock_export.side_effect = ExportError(Path("x.csv"), "Permission denied")

        with self.assertRaises(SystemExit) as ctx:
            main(["--all"])
        self.assertEqual(ctx.exception.code, 1)

    @patch("scraper.main.print_summary")
    @patch("scraper.main.export_csv")
    @patch("scraper.main.BooksParser")
    @patch("scraper.main.BooksFetcher")
    def test_empty_result_skips_export(
        self, mock_fetcher_cls, mock_parser_cls, mock_export, mock_summary
    ):
        mock_fetcher = MagicMock()
        mock_fetcher_cls.return_value.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_parser = mock_parser_cls.return_value
        mock_parser.scrape_catalog.return_value = []

        main(["--all"])
        mock_export.assert_not_called()
        mock_summary.assert_called_once_with([])

    @patch("scraper.main.BooksFetcher")
    def test_pages_zero_exits_1(self, mock_fetcher_cls):
        with self.assertRaises(SystemExit) as ctx:
            main(["--pages", "0"])
        self.assertEqual(ctx.exception.code, 1)

    @patch("scraper.main.export_csv")
    @patch("scraper.main.BooksParser")
    @patch("scraper.main.BooksFetcher")
    def test_output_dir_passed(self, mock_fetcher_cls, mock_parser_cls, mock_export):
        mock_fetcher = MagicMock()
        mock_fetcher_cls.return_value.__enter__ = MagicMock(return_value=mock_fetcher)
        mock_fetcher_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_parser = mock_parser_cls.return_value
        mock_parser.scrape_catalog.return_value = _sample_books()
        mock_export.return_value = Path("custom_dir/books.csv")

        main(["--all", "--output-dir", "custom_dir"])
        args, kwargs = mock_export.call_args
        self.assertEqual(args[1], "custom_dir")


if __name__ == "__main__":
    unittest.main()
