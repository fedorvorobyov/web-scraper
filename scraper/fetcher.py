"""HTTP fetcher with retry logic, rate limiting, and logging.

Usage::

    with BooksFetcher(max_retries=3) as fetcher:
        html = fetcher.fetch("https://books.toscrape.com/")
"""

import logging
import time
from typing import Optional

import requests

__all__ = ["BooksFetcher", "FetchError"]

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; BooksScraperBot/1.0; "
    "+https://github.com/user/web-scraper)"
)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class FetchError(Exception):
    """Raised when a page cannot be fetched after all retry attempts."""

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to fetch {url}: {reason}")


class BooksFetcher:
    """HTTP client with retry (exponential backoff), rate limiting,
    and per-request logging."""

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        delay_between_requests: float = 1.0,
        timeout: int = 10,
    ) -> None:
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._delay = delay_between_requests
        self._timeout = timeout
        self._request_count = 0
        self._last_request_time: Optional[float] = None

        self._session = requests.Session()
        self._session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

        logger.info(
            "Fetcher initialized (max_retries=%d, backoff=%.1f, "
            "delay=%.1fs, timeout=%ds)",
            max_retries, backoff_factor, delay_between_requests, timeout,
        )

    # -- Context Manager ---------------------------------------------------

    def __enter__(self) -> "BooksFetcher":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # -- Public API --------------------------------------------------------

    @property
    def request_count(self) -> int:
        """Total number of HTTP requests made (including retries)."""
        return self._request_count

    def fetch(self, url: str) -> str:
        """Fetch a page and return its HTML as a string.

        Applies rate limiting before the request and retries with
        exponential backoff on transient failures.

        Raises:
            FetchError: After all retries exhausted or on non-retryable
                HTTP status (e.g. 404).
        """
        self._wait_for_rate_limit()

        last_exception: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                backoff = self._backoff_factor * (2 ** (attempt - 1))
                logger.warning(
                    "Retry %d/%d for %s in %.1fs",
                    attempt, self._max_retries, url, backoff,
                )
                time.sleep(backoff)

            try:
                self._request_count += 1
                start = time.monotonic()
                response = self._session.get(url, timeout=self._timeout)
                elapsed = time.monotonic() - start

                self._last_request_time = time.monotonic()

                if response.status_code == 200:
                    logger.info("OK %s (%.2fs)", url, elapsed)
                    return response.text

                if response.status_code in RETRYABLE_STATUS_CODES:
                    logger.warning(
                        "HTTP %d for %s (%.2fs) - will retry",
                        response.status_code, url, elapsed,
                    )
                    last_exception = FetchError(
                        url, f"HTTP {response.status_code}",
                    )
                    continue

                raise FetchError(
                    url,
                    f"HTTP {response.status_code} (non-retryable)",
                )

            except requests.ConnectionError as e:
                logger.warning("Connection error for %s: %s", url, e)
                last_exception = e
            except requests.Timeout as e:
                logger.warning("Timeout for %s: %s", url, e)
                last_exception = e

        raise FetchError(
            url,
            f"All {self._max_retries + 1} attempts failed. "
            f"Last error: {last_exception}",
        )

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()
        logger.info(
            "Fetcher closed. Total requests made: %d",
            self._request_count,
        )

    # -- Private -----------------------------------------------------------

    def _wait_for_rate_limit(self) -> None:
        """Sleep if not enough time has passed since the last request."""
        if self._last_request_time is None:
            return

        elapsed = time.monotonic() - self._last_request_time
        remaining = self._delay - elapsed

        if remaining > 0:
            logger.debug(
                "Rate limit: sleeping %.2fs before next request",
                remaining,
            )
            time.sleep(remaining)
