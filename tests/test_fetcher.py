"""Unit tests for scraper.fetcher module."""

import unittest
from unittest.mock import patch, MagicMock

from scraper.fetcher import BooksFetcher, FetchError


class TestBooksFetcher(unittest.TestCase):
    """Tests for BooksFetcher class."""

    def _make_response(self, status_code=200, text="<html></html>"):
        """Helper: create a mock requests.Response."""
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        return resp

    @patch("scraper.fetcher.requests.Session")
    def test_fetch_success(self, mock_session_cls):
        """fetch() returns HTML string on 200 OK."""
        mock_session = mock_session_cls.return_value
        mock_session.get.return_value = self._make_response(200, "<p>ok</p>")

        with BooksFetcher(delay_between_requests=0) as f:
            result = f.fetch("http://example.com")

        self.assertEqual(result, "<p>ok</p>")
        self.assertEqual(f.request_count, 1)

    @patch("scraper.fetcher.requests.Session")
    def test_fetch_retry_on_500(self, mock_session_cls):
        """fetch() retries on 500 and succeeds on next attempt."""
        mock_session = mock_session_cls.return_value
        mock_session.get.side_effect = [
            self._make_response(500),
            self._make_response(200, "<p>ok</p>"),
        ]

        with BooksFetcher(
            max_retries=2, backoff_factor=0.01, delay_between_requests=0
        ) as f:
            result = f.fetch("http://example.com")

        self.assertEqual(result, "<p>ok</p>")
        self.assertEqual(mock_session.get.call_count, 2)

    @patch("scraper.fetcher.requests.Session")
    def test_fetch_raises_on_404(self, mock_session_cls):
        """fetch() raises FetchError immediately on 404 (non-retryable)."""
        mock_session = mock_session_cls.return_value
        mock_session.get.return_value = self._make_response(404)

        with BooksFetcher(delay_between_requests=0) as f:
            with self.assertRaises(FetchError) as ctx:
                f.fetch("http://example.com/missing")

        self.assertIn("404", str(ctx.exception))
        self.assertEqual(mock_session.get.call_count, 1)

    @patch("scraper.fetcher.requests.Session")
    def test_fetch_all_retries_exhausted(self, mock_session_cls):
        """fetch() raises FetchError after all retries are exhausted."""
        mock_session = mock_session_cls.return_value
        mock_session.get.return_value = self._make_response(503)

        with BooksFetcher(
            max_retries=2, backoff_factor=0.01, delay_between_requests=0
        ) as f:
            with self.assertRaises(FetchError):
                f.fetch("http://example.com")

        # 1 initial + 2 retries = 3 total
        self.assertEqual(mock_session.get.call_count, 3)

    @patch("scraper.fetcher.time.sleep")
    @patch("scraper.fetcher.requests.Session")
    def test_rate_limiting(self, mock_session_cls, mock_sleep):
        """Two consecutive fetch() calls trigger a rate-limit sleep."""
        mock_session = mock_session_cls.return_value
        mock_session.get.return_value = self._make_response(200)

        with BooksFetcher(delay_between_requests=2.0) as f:
            f.fetch("http://example.com/page-1")
            f.fetch("http://example.com/page-2")

        # sleep should have been called for rate limiting on the second request
        self.assertTrue(mock_sleep.called)

    @patch("scraper.fetcher.time.sleep")
    @patch("scraper.fetcher.requests.Session")
    def test_exponential_backoff_delays(self, mock_session_cls, mock_sleep):
        """Backoff delays follow factor * 2^(attempt-1) pattern."""
        mock_session = mock_session_cls.return_value
        mock_session.get.return_value = self._make_response(500)

        with BooksFetcher(
            max_retries=3, backoff_factor=1.0, delay_between_requests=0
        ) as f:
            with self.assertRaises(FetchError):
                f.fetch("http://example.com")

        # Expected backoff sleeps: 1.0, 2.0, 4.0
        sleep_values = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertIn(1.0, sleep_values)
        self.assertIn(2.0, sleep_values)
        self.assertIn(4.0, sleep_values)

    @patch("scraper.fetcher.requests.Session")
    def test_fetch_retry_on_connection_error(self, mock_session_cls):
        """fetch() retries on ConnectionError."""
        import requests as real_requests

        mock_session = mock_session_cls.return_value
        mock_session.get.side_effect = [
            real_requests.ConnectionError("Connection refused"),
            self._make_response(200, "<p>recovered</p>"),
        ]

        with BooksFetcher(
            max_retries=2, backoff_factor=0.01, delay_between_requests=0
        ) as f:
            result = f.fetch("http://example.com")

        self.assertEqual(result, "<p>recovered</p>")
        self.assertEqual(mock_session.get.call_count, 2)

    @patch("scraper.fetcher.requests.Session")
    def test_fetch_retry_on_timeout(self, mock_session_cls):
        """fetch() retries on Timeout."""
        import requests as real_requests

        mock_session = mock_session_cls.return_value
        mock_session.get.side_effect = [
            real_requests.Timeout("Read timed out"),
            self._make_response(200, "<p>ok</p>"),
        ]

        with BooksFetcher(
            max_retries=2, backoff_factor=0.01, delay_between_requests=0
        ) as f:
            result = f.fetch("http://example.com")

        self.assertEqual(result, "<p>ok</p>")

    @patch("scraper.fetcher.requests.Session")
    def test_request_count_includes_retries(self, mock_session_cls):
        """request_count includes both initial attempts and retries."""
        mock_session = mock_session_cls.return_value
        mock_session.get.side_effect = [
            self._make_response(500),
            self._make_response(500),
            self._make_response(200, "<p>ok</p>"),
        ]

        with BooksFetcher(
            max_retries=3, backoff_factor=0.01, delay_between_requests=0
        ) as f:
            f.fetch("http://example.com")

        self.assertEqual(f.request_count, 3)

    @patch("scraper.fetcher.requests.Session")
    def test_context_manager_closes_session(self, mock_session_cls):
        """Session is closed when exiting context manager."""
        mock_session = mock_session_cls.return_value

        with BooksFetcher(delay_between_requests=0):
            pass

        mock_session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
