"""HTML parser for books.toscrape.com catalog pages.

Pure parsing functions accept HTML strings and return data.
BooksParser orchestrator ties fetcher and parsing together.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.fetcher import BooksFetcher

__all__ = [
    "Book", "BooksParser", "ParseError",
    "parse_catalog_page", "parse_next_page_url",
    "parse_categories", "parse_book_detail",
]

logger = logging.getLogger(__name__)

BASE_URL = "https://books.toscrape.com/"
CATALOG_URL = "https://books.toscrape.com/catalogue/page-{}.html"

RATING_MAP = {
    "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5,
}


@dataclass
class Book:
    """A single book's data."""
    title: str
    price: float
    rating: int
    availability: bool
    category: str
    url: str


class ParseError(Exception):
    """Raised when HTML cannot be parsed as expected."""

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Parse error for {url}: {reason}")


# -- Private helpers -------------------------------------------------------

def _parse_rating(element: BeautifulSoup) -> int:
    """Extract star rating (1-5) from an element containing p.star-rating."""
    tag = element.select_one("p.star-rating")
    if tag is None:
        return 0
    for cls in tag.get("class", []):
        if cls in RATING_MAP:
            return RATING_MAP[cls]
    return 0


def _parse_price(text: str) -> float:
    """Extract numeric price from a string like '£51.77'."""
    match = re.search(r"[\d.]+", text)
    if match is None:
        raise ValueError(f"Cannot parse price from: {text!r}")
    return float(match.group())


# -- Pure parsing functions ------------------------------------------------

def parse_catalog_page(
    html: str,
    base_url: str,
    category: str = "",
) -> list[Book]:
    """Parse a catalog/category listing page and return a list of Books."""
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select("article.product_pod")

    books: list[Book] = []
    for article in articles:
        link = article.select_one("h3 a")
        if link is None:
            logger.warning("Skipping article without title link on %s", base_url)
            continue

        title = link.get("title", link.get_text(strip=True))
        href = link.get("href", "")
        book_url = urljoin(base_url, href)

        price_tag = article.select_one(".price_color")
        try:
            price = _parse_price(price_tag.get_text(strip=True)) if price_tag else 0.0
        except ValueError:
            logger.warning("Cannot parse price for '%s', defaulting to 0.0", title)
            price = 0.0

        rating = _parse_rating(article)

        avail_tag = article.select_one(".availability")
        in_stock = False
        if avail_tag:
            in_stock = "in stock" in avail_tag.get_text(strip=True).lower()

        books.append(Book(
            title=title,
            price=price,
            rating=rating,
            availability=in_stock,
            category=category,
            url=book_url,
        ))

    logger.info("Parsed %d books from %s", len(books), base_url)
    return books


def parse_next_page_url(html: str, current_url: str) -> Optional[str]:
    """Extract the URL of the next page. Returns None on the last page."""
    soup = BeautifulSoup(html, "lxml")
    next_link = soup.select_one("li.next a")
    if next_link is None:
        return None
    href = next_link.get("href", "")
    return urljoin(current_url, href)


def parse_categories(html: str, base_url: str) -> dict[str, str]:
    """Parse the sidebar and return {category_name: absolute_url}."""
    soup = BeautifulSoup(html, "lxml")
    links = soup.select("div.side_categories ul li ul li a")

    categories: dict[str, str] = {}
    for link in links:
        name = link.get_text(strip=True)
        href = link.get("href", "")
        categories[name] = urljoin(base_url, href)

    logger.info("Found %d categories", len(categories))
    return categories


def parse_book_detail(html: str, url: str) -> Book:
    """Parse a single book's detail page for complete data.

    Raises:
        ParseError: If <h1> (title) is not found.
    """
    soup = BeautifulSoup(html, "lxml")

    h1 = soup.select_one("h1")
    if h1 is None:
        raise ParseError(url, "No <h1> found on book detail page")
    title = h1.get_text(strip=True)

    price_tag = soup.select_one(".price_color")
    try:
        price = _parse_price(price_tag.get_text(strip=True)) if price_tag else 0.0
    except ValueError:
        logger.warning("Cannot parse price for '%s', defaulting to 0.0", title)
        price = 0.0

    rating = _parse_rating(soup)

    avail_tag = soup.select_one("p.instock.availability")
    in_stock = False
    if avail_tag:
        in_stock = "in stock" in avail_tag.get_text(strip=True).lower()

    breadcrumbs = soup.select("ul.breadcrumb li")
    category = ""
    if len(breadcrumbs) >= 3:
        category = breadcrumbs[2].get_text(strip=True)

    return Book(
        title=title,
        price=price,
        rating=rating,
        availability=in_stock,
        category=category,
        url=url,
    )


# -- Orchestrator ----------------------------------------------------------

class BooksParser:
    """High-level orchestrator: fetches pages via BooksFetcher
    and parses them into Book objects."""

    def __init__(self, fetcher: BooksFetcher) -> None:
        self._fetcher = fetcher

    def get_categories(self) -> dict[str, str]:
        """Fetch the homepage and return available categories."""
        html = self._fetcher.fetch(BASE_URL)
        return parse_categories(html, BASE_URL)

    def scrape_catalog(self, max_pages: int = 0) -> list[Book]:
        """Scrape the general catalog.

        Args:
            max_pages: Maximum pages to scrape. 0 means all.
        """
        all_books: list[Book] = []
        current_url: Optional[str] = CATALOG_URL.format(1)
        page_num = 0

        while current_url is not None:
            page_num += 1
            if max_pages > 0 and page_num > max_pages:
                break

            html = self._fetcher.fetch(current_url)
            books = parse_catalog_page(html, current_url)
            all_books.extend(books)

            logger.info(
                "Page %d - %d books found (total: %d)",
                page_num, len(books), len(all_books),
            )

            current_url = parse_next_page_url(html, current_url)

        logger.info(
            "Catalog scraping complete: %d books from %d pages",
            len(all_books), page_num,
        )
        return all_books

    def scrape_category(
        self,
        category_name: str,
        max_pages: int = 0,
    ) -> list[Book]:
        """Scrape all books from a specific category.

        Raises:
            ParseError: If the category is not found.
        """
        categories = self.get_categories()

        target_url: Optional[str] = None
        matched_name: str = ""
        for name, url in categories.items():
            if name.lower() == category_name.lower():
                target_url = url
                matched_name = name
                break

        if target_url is None:
            available = ", ".join(sorted(categories.keys()))
            raise ParseError(
                BASE_URL,
                f"Category '{category_name}' not found. "
                f"Available: {available}",
            )

        all_books: list[Book] = []
        current_url: Optional[str] = target_url
        page_num = 0

        while current_url is not None:
            page_num += 1
            if max_pages > 0 and page_num > max_pages:
                break

            html = self._fetcher.fetch(current_url)
            books = parse_catalog_page(html, current_url, category=matched_name)
            all_books.extend(books)

            logger.info(
                "Category '%s' page %d - %d books (total: %d)",
                matched_name, page_num, len(books), len(all_books),
            )

            current_url = parse_next_page_url(html, current_url)

        logger.info(
            "Category '%s' complete: %d books from %d pages",
            matched_name, len(all_books), page_num,
        )
        return all_books
