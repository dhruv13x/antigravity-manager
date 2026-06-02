from datetime import datetime, timezone
from antigravity_manager.utils import isoformat_local, safe_label, build_archive_name

def test_isoformat_local():
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert isoformat_local(dt) == "2024-01-01T12:00:00+00:00"

def test_safe_label():
    assert safe_label("user@example.com") == "user@example.com"
    assert safe_label("a b") == "a_b"
    assert safe_label(None) == "unknown"

def test_build_archive_name():
    dt = datetime(2024, 1, 1, 12, 0, 0)
    assert build_archive_name(dt, "user") == "20240101_120000-user-antigravity.tar.gz"
