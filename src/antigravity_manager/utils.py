from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def isoformat_local(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.astimezone().isoformat(timespec="seconds")
    return dt.isoformat(timespec="seconds")


def safe_label(value: str | None) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9@._-]+", "_", value or "unknown")
    return cleaned.strip("._-") or "unknown"


def build_archive_name(captured_at: datetime, email: str | None) -> str:
    return f"{safe_label(email)}-latest-antigravity.tar.gz"


def read_active_email(antigravity_home: Path | None = None) -> str | None:
    from .config import ACTIVE_ACCOUNT_PATH

    # 1. Try AGM's active account tracking first (usually most reliable)
    if ACTIVE_ACCOUNT_PATH.exists():
        try:
            data = json.loads(ACTIVE_ACCOUNT_PATH.read_text(encoding="utf-8"))
            email = data.get("email")
            if isinstance(email, str) and email.strip():
                return email.strip()
        except Exception:
            pass

    # 2. Fallback to Antigravity CLI's own record
    if antigravity_home:
        try:
            path = antigravity_home / "google_accounts.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            active = data.get("active")
            if isinstance(active, str) and active.strip():
                return active.strip()
        except Exception:
            pass

    return None
