import json
import unittest
from unittest.mock import Mock

from brain_v12.brain.binance_readonly_client import (
    BinanceReadOnlyClient,
    BinanceReadOnlyError,
)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = json.dumps(payload).encode()
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class BinanceReadOnlyClientTests(unittest.TestCase):
    def make_client(self, payload, status=200):
        opener = Mock(return_value=FakeResponse(payload, status))
        return BinanceReadOnlyClient(opener=opener), opener

    def test_ping_reports_read_only_connection(self):
        client, opener = self.make_client({})
        self.assertEqual(client.ping(), {"connected": True, "read_only": True})
        request = opener.call_args.args[0]
        self.assertEqual(request.method, "GET")
        self.assertIn("/api/v3/ping", request.full_url)

    def test_price_uses_public_endpoint_and_symbol(self):
        client, opener = self.make_client({"symbol": "BTCUSDT", "price": "65000.00"})
        self.assertEqual(client.price("btcusdt"), {"symbol": "BTCUSDT", "price": "65000.00"})
        self.assertIn("/api/v3/ticker/price?symbol=BTCUSDT", opener.call_args.args[0].full_url)

    def test_rejects_non_https_base_url(self):
        with self.assertRaises(ValueError):
            BinanceReadOnlyClient(base_url="http://api.binance.com")

    def test_rejects_non_allowlisted_endpoint(self):
        client, _ = self.make_client({})
        with self.assertRaises(ValueError):
            client._get("/api/v3/order")

    def test_rejects_invalid_symbol(self):
        client, _ = self.make_client({"symbol": "BTCUSDT", "price": "1"})
        with self.assertRaises(ValueError):
            client.price("BTC/USDT")

    def test_rejects_unexpected_ticker_payload(self):
        client, _ = self.make_client({"symbol": "ETHUSDT", "price": "1"})
        with self.assertRaises(BinanceReadOnlyError):
            client.price("BTCUSDT")

    def test_rejects_http_error_without_leaking_response(self):
        client, _ = self.make_client({"msg": "sensitive"}, status=403)
        with self.assertRaisesRegex(BinanceReadOnlyError, "HTTP 403"):
            client.ping()


if __name__ == "__main__":
    unittest.main()
