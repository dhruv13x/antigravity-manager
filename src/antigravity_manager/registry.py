from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import COOLDOWN_REGISTRY_PATH
from .status import LiveStatus, status_to_dict


def load_registry(path: Path = COOLDOWN_REGISTRY_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_registry(data: dict[str, dict[str, Any]], path: Path = COOLDOWN_REGISTRY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def update_registry_from_status(status: LiveStatus, *, dry_run: bool = False) -> None:
    registry = load_registry()
    next_refreshes = [model.refresh_at for model in status.models if model.refresh_at is not None]
    next_available_at = (
        max(next_refreshes).isoformat() if next_refreshes else status.captured_at.isoformat()
    )
    registry[status.email] = {
        "schema_version": 1,
        "product": "antigravity",
        "email": status.email,
        "plan": status.plan,
        "is_pro": status.is_pro,
        "captured_at": status.captured_at.isoformat(),
        "updated_at": datetime.now().astimezone().isoformat(),
        "next_available_at": next_available_at,
        "status": status_to_dict(status),
    }
    if not dry_run:
        save_registry(registry)
