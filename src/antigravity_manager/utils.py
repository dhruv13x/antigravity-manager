from __future__ import annotations

import re
from datetime import datetime


def isoformat_local(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.astimezone().isoformat(timespec="seconds")
    return dt.isoformat(timespec="seconds")


def safe_label(value: str | None) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9@._-]+", "_", value or "unknown")
    return cleaned.strip("._-") or "unknown"


def build_archive_name(captured_at: datetime, email: str | None) -> str:
    return f"{captured_at.strftime('%Y-%m-%d-%H%M%S')}-" f"{safe_label(email)}-antigravity.tar.gz"
