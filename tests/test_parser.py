"""Unit tests for scraper.parser module."""

import unittest
from unittest.mock import MagicMock

from scraper.fetcher import BooksFetcher


# -- Mock HTML fixtures ---------------------------------------------------

CATALOG_PAGE_HTML = """
<html>
<body>
<div class="side_categories">
  <ul><li><a href="catalogue/category/books_1/index.html">Books</a>
    <ul>
      <li><a href="catalogue/category/books/travel_2/index.html">Travel</a></li>
      <li><a href="catalogue/category/books/science_22/index.html">Science</a></li>
    </ul>
  </li></ul>
</div>
<section>
  <ol class="row">
    <li>
      <article class="product_pod">
        <p class="star-rating Three"></p>
        <h3><a href="catalogue/a-light-in-the-attic_1000/index.html"
               title="A Light in the Attic">A Light in the ...</a></h3>
        <div class="product_price">
          <p class="price_color">£51.77</p>
          <p class="instock availability"><i class="icon-ok"></i> In stock</p>
        </div>
      </article>
    </li>
    <li>
      <article class="product_pod">
        <p class="star-rating One"></p>
        <h3><a href="catalogue/tipping-the-velvet_999/index.html"
               title="Tipping the Velvet">Tipping the ...</a></h3>
        <div class="product_price">
          <p class="price_color">£53.74</p>
          <p class="instock availability"><i class="icon-ok"></i> In stock</p>
        </div>
      </article>
    </li>
  </ol>
  <ul class="pager">
    <li class="next"><a href="page-2.html">next</a></li>
  </ul>
</section>
</body>
</html>
"""

LAST_PAGE_HTML = """
<html><body>
<section>
  <ol class="row">
    <li>
      <article class="product_pod">
        <p class="star-rating Five"></p>
        <h3><a href="catalogue/last-book_1/index.html"
               title="Last Book">Last ...</a></h3>
        <div class="product_price">
          <p class="price_color">£10.00</p>
          <p class="instock availability"> In stock </p>
        </div>
      </article>
    </li>
  </ol>
  <ul class="pager">
    <li class="previous"><a href="page-49.html">previous</a></li>
  </ul>
</section>
</body></html>
"""

OUT_OF_STOCK_HTML = """
<html><body>
<section>
  <ol class="row">
    <li>
      <article class="product_pod">
        <p class="star-rating Two"></p>
        <h3><a href="catalogue/sold-out_1/index.html"
               title="Sold Out Book">Sold ...</a></h3>
        <div class="product_price">
          <p class="price_color">£25.00</p>
          <p class="availability">Out of stock</p>
        </div>
      </article>
    </li>
  </ol>
</section>
</body></html>
"""

BOOK_DETAIL_HTML = """
<html><body>
<ul class="breadcrumb">
  <li><a href="../../../index.html">Home</a></li>
  <li><a href="../../../catalogue/category/books_1/index.html">Books</a></li>
  <li><a href="../../../catalogue/category/books/science_22/index.html">Science</a></li>
  <li class="active">The Grand Design</li>
</ul>
<div class="product_main">
  <h1>The Grand Design</h1>
  <p class="star-rating Four"></p>
  <p class="price_color">£13.76</p>
  <p class="instock availability">
    <i class="icon-ok"></i> In stock (22 available)
  </p>
</div>
</body></html>
"""

BASE_URL = "https://books.toscrape.com/"


class TestParsePrice(unittest.TestCase):
    """Tests for _parse_price helper."""

    def test_parse_price_valid(self):
        from scraper.parser import _parse_price
        self.assertAlmostEqual(_parse_price("£51.77"), 51.77)

    def test_parse_price_no_symbol(self):
        from scraper.parser import _parse_price
        self.assertAlmostEqual(_parse_price("10.00"), 10.0)

    def test_parse_price_invalid(self):
        from scraper.parser import _parse_price
        with self.assertRaises(ValueError):
            _parse_price("free")


class TestParseRating(unittest.TestCase):
    """Tests for _parse_rating helper."""

    def test_all_rating_values(self):
        from scraper.parser import _parse_rating
        from bs4 import BeautifulSoup

        for word, expected in [("One", 1), ("Two", 2), ("Three", 3),
                               ("Four", 4), ("Five", 5)]:
            html = f'<article><p class="star-rating {word}"></p></article>'
            soup = BeautifulSoup(html, "lxml")
            self.assertEqual(_parse_rating(soup), expected, f"Failed for {word}")

    def test_missing_rating(self):
        from scraper.parser import _parse_rating
        from bs4 import BeautifulSoup

        html = "<article></article>"
        soup = BeautifulSoup(html, "lxml")
        self.assertEqual(_parse_rating(soup), 0)


class TestParseCatalogPage(unittest.TestCase):
    """Tests for parse_catalog_page function."""

    def test_extracts_books(self):
        from scraper.parser import parse_catalog_page
        books = parse_catalog_page(CATALOG_PAGE_HTML, BASE_URL)
        self.assertEqual(len(books), 2)

    def test_title(self):
        from scraper.parser import parse_catalog_page
        books = parse_catalog_page(CATALOG_PAGE_HTML, BASE_URL)
        self.assertEqual(books[0].title, "A Light in the Attic")

    def test_price(self):
        from scraper.parser import parse_catalog_page
        books = parse_catalog_page(CATALOG_PAGE_HTML, BASE_URL)
        self.assertAlmostEqual(books[0].price, 51.77)

    def test_rating(self):
        from scraper.parser import parse_catalog_page
        books = parse_catalog_page(CATALOG_PAGE_HTML, BASE_URL)
        self.assertEqual(books[0].rating, 3)
        self.assertEqual(books[1].rating, 1)

    def test_availability_in_stock(self):
        from scraper.parser import parse_catalog_page
        books = parse_catalog_page(CATALOG_PAGE_HTML, BASE_URL)
        self.assertTrue(books[0].availability)

    def test_url_resolution(self):
        from scraper.parser import parse_catalog_page
        books = parse_catalog_page(CATALOG_PAGE_HTML, BASE_URL)
        self.assertTrue(books[0].url.startswith("https://"))
        self.assertIn("a-light-in-the-attic", books[0].url)

    def test_with_category(self):
        from scraper.parser import parse_catalog_page
        books = parse_catalog_page(CATALOG_PAGE_HTML, BASE_URL, category="Science")
        for book in books:
            self.assertEqual(book.category, "Science")

    def test_empty_html(self):
        from scraper.parser import parse_catalog_page
        books = parse_catalog_page("<html></html>", BASE_URL)
        self.assertEqual(books, [])

    def test_out_of_stock(self):
        from scraper.parser import parse_catalog_page
        books = parse_catalog_page(OUT_OF_STOCK_HTML, BASE_URL)
        self.assertEqual(len(books), 1)
        self.assertFalse(books[0].availability)


class TestParseNextPageUrl(unittest.TestCase):
    """Tests for parse_next_page_url function."""

    def test_next_page_exists(self):
        from scraper.parser import parse_next_page_url
        url = parse_next_page_url(CATALOG_PAGE_HTML, BASE_URL)
        self.assertIsNotNone(url)
        self.assertIn("page-2", url)

    def test_last_page(self):
        from scraper.parser import parse_next_page_url
        url = parse_next_page_url(LAST_PAGE_HTML, BASE_URL)
        self.assertIsNone(url)


class TestParseCategories(unittest.TestCase):
    """Tests for parse_categories function."""

    def test_extracts_categories(self):
        from scraper.parser import parse_categories
        cats = parse_categories(CATALOG_PAGE_HTML, BASE_URL)
        self.assertIn("Travel", cats)
        self.assertIn("Science", cats)
        self.assertEqual(len(cats), 2)

    def test_empty_sidebar(self):
        from scraper.parser import parse_categories
        cats = parse_categories("<html></html>", BASE_URL)
        self.assertEqual(cats, {})

    def test_urls_are_absolute(self):
        from scraper.parser import parse_categories
        cats = parse_categories(CATALOG_PAGE_HTML, BASE_URL)
        for url in cats.values():
            self.assertTrue(url.startswith("https://"))


class TestParseBookDetail(unittest.TestCase):
    """Tests for parse_book_detail function."""

    def test_full_parsing(self):
        from scraper.parser import parse_book_detail
        book_url = "https://books.toscrape.com/catalogue/the-grand-design_405/index.html"
        book = parse_book_detail(BOOK_DETAIL_HTML, book_url)
        self.assertEqual(book.title, "The Grand Design")
        self.assertAlmostEqual(book.price, 13.76)
        self.assertEqual(book.rating, 4)
        self.assertTrue(book.availability)
        self.assertEqual(book.url, book_url)

    def test_category_from_breadcrumb(self):
        from scraper.parser import parse_book_detail
        book = parse_book_detail(BOOK_DETAIL_HTML, "http://example.com")
        self.assertEqual(book.category, "Science")

    def test_missing_h1_raises(self):
        from scraper.parser import parse_book_detail, ParseError
        with self.assertRaises(ParseError):
            parse_book_detail("<html><body></body></html>", "http://example.com")


class TestBooksParser(unittest.TestCase):
    """Tests for BooksParser orchestrator."""

    def test_scrape_catalog_with_max_pages(self):
        from scraper.parser import BooksParser
        mock_fetcher = MagicMock(spec=BooksFetcher)
        mock_fetcher.fetch.side_effect = [
            CATALOG_PAGE_HTML,  # page 1 (has next)
            LAST_PAGE_HTML,     # page 2 (no next)
        ]
        parser = BooksParser(mock_fetcher)
        books = parser.scrape_catalog(max_pages=2)
        self.assertEqual(mock_fetcher.fetch.call_count, 2)
        self.assertEqual(len(books), 3)  # 2 from page 1 + 1 from page 2

    def test_scrape_catalog_stops_at_last_page(self):
        from scraper.parser import BooksParser
        mock_fetcher = MagicMock(spec=BooksFetcher)
        mock_fetcher.fetch.side_effect = [LAST_PAGE_HTML]
        parser = BooksParser(mock_fetcher)
        books = parser.scrape_catalog(max_pages=0)
        self.assertEqual(mock_fetcher.fetch.call_count, 1)
        self.assertEqual(len(books), 1)

    def test_scrape_category_found(self):
        from scraper.parser import BooksParser
        mock_fetcher = MagicMock(spec=BooksFetcher)
        mock_fetcher.fetch.side_effect = [
            CATALOG_PAGE_HTML,  # homepage for categories
            LAST_PAGE_HTML,     # category page (no next)
        ]
        parser = BooksParser(mock_fetcher)
        books = parser.scrape_category("Science")
        self.assertEqual(len(books), 1)
        for book in books:
            self.assertEqual(book.category, "Science")

    def test_scrape_category_not_found(self):
        from scraper.parser import BooksParser, ParseError
        mock_fetcher = MagicMock(spec=BooksFetcher)
        mock_fetcher.fetch.return_value = CATALOG_PAGE_HTML
        parser = BooksParser(mock_fetcher)
        with self.assertRaises(ParseError):
            parser.scrape_category("Nonexistent")

    def test_scrape_category_case_insensitive(self):
        from scraper.parser import BooksParser
        mock_fetcher = MagicMock(spec=BooksFetcher)
        mock_fetcher.fetch.side_effect = [
            CATALOG_PAGE_HTML,  # homepage
            LAST_PAGE_HTML,     # category page
        ]
        parser = BooksParser(mock_fetcher)
        books = parser.scrape_category("science")  # lowercase
        self.assertTrue(len(books) > 0)

    def test_get_categories(self):
        from scraper.parser import BooksParser
        mock_fetcher = MagicMock(spec=BooksFetcher)
        mock_fetcher.fetch.return_value = CATALOG_PAGE_HTML
        parser = BooksParser(mock_fetcher)
        cats = parser.get_categories()
        self.assertIn("Travel", cats)
        self.assertIn("Science", cats)


if __name__ == "__main__":
    unittest.main()
