# Binance read-only API client

Electronic Brain's Binance integration starts with a deliberately public-only
Spot API client. It does not accept API credentials and cannot access account
balances, place/cancel orders, withdraw, or transfer funds.

## Supported checks

- `ping()`: public API reachability.
- `server_time()`: public server clock.
- `price("BTCUSDT")`: public ticker price.
- `exchange_info("BTCUSDT")`: public symbol metadata.

All requests use HTTPS and GET, with a short timeout and an endpoint allowlist.
Tests use mocked responses and do not contact Binance or perform financial actions.

## Run tests

```bash
python -m unittest brain_v12.tests.test_binance_readonly_client -v
```

A successful mocked test proves client behavior only. A real `ping()` response
is required to claim live connectivity. Authenticated account-read access is a
separate future change and must use a restricted read-only key stored outside
the repository. Never enable trading or withdrawal permissions for Brain.
