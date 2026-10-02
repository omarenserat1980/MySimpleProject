from datetime import datetime, timezone, timedelta
import pytest
from brain_v12.business.crypto_market_snapshot import MarketSnapshot


def test_fresh_snapshot():
    now=datetime(2026,10,2,12,0,tzinfo=timezone.utc)
    s=MarketSnapshot("BTC",0.04,"2026-10-02T06:00:00Z","test")
    result=s.validate(max_age_hours=24,now=now)
    assert result["freshness"]=="FRESH"


def test_stale_snapshot():
    now=datetime(2026,10,2,12,0,tzinfo=timezone.utc)
    s=MarketSnapshot("BTC",0.04,"2026-09-30T12:00:00Z","test")
    assert s.freshness(max_age_hours=24,now=now)=="STALE"


def test_timezone_is_required():
    s=MarketSnapshot("BTC",0.04,"2026-10-02T06:00:00","test")
    with pytest.raises(ValueError):
        s.observed_datetime()
