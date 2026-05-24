import pytest
from datetime import datetime, timezone
from antigravity_manager.utils import isoformat_local, safe_label, build_archive_name

def test_isoformat_local():
    dt = datetime(2023, 1, 1, 12, 0, 0)
    res = isoformat_local(dt)
    assert "2023-01-01T12:00:00" in res

    dt_tz = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    res_tz = isoformat_local(dt_tz)
    assert res_tz == "2023-01-01T12:00:00+00:00"

def test_safe_label():
    assert safe_label("valid_123@abc.com") == "valid_123@abc.com"
    assert safe_label("invalid ! chars") == "invalid_chars"
    assert safe_label("---only-dashes") == "only-dashes"
    assert safe_label("") == "unknown"
    assert safe_label(None) == "unknown"

def test_build_archive_name():
    dt = datetime(2023, 1, 1, 12, 30, 45)
    name = build_archive_name(dt, "test@test.com")
    assert name == "2023-01-01-123045-test@test.com-antigravity.tar.gz"

    name_none = build_archive_name(dt, None)
    assert name_none == "2023-01-01-123045-unknown-antigravity.tar.gz"
