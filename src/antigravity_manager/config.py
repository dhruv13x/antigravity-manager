from __future__ import annotations

import os
from pathlib import Path


def _home_from_env(name: str, fallback: str) -> Path:
    return Path(os.path.expanduser(os.environ.get(name, fallback)))


AGM_HOME = _home_from_env("AGM_HOME", "~/.antigravity-manager")
DEFAULT_BACKUP_DIR = AGM_HOME / "backups"
COOLDOWN_REGISTRY_PATH = AGM_HOME / "cooldown.json"
ACTIVE_ACCOUNT_PATH = AGM_HOME / "active.json"
SAFETY_BACKUP_DIR = AGM_HOME / "safety_backups"

GEMINI_HOME = _home_from_env("GEMINI_HOME", "~/.gemini")
GEMINI_CONFIG_DIR = _home_from_env("GEMINI_CONFIG_DIR", str(GEMINI_HOME / "config"))
ANTIGRAVITY_HOME = _home_from_env(
    "ANTIGRAVITY_HOME",
    str(GEMINI_HOME / "antigravity-cli"),
)
ANTIGRAVITY_SESSION_DIR = _home_from_env("ANTIGRAVITY_SESSION_DIR", "~/.antigravitycli")

ANTIGRAVITY_AUTH_FILES = (
    "antigravity-oauth-token",
    "installation_id",
    "settings.json",
    "cache/onboarding.json",
)

EXCLUDED_TOP_LEVEL_NAMES: set[str] = set()

DEFAULT_COOLDOWN_DISPLAY_LIMIT = 200
DEFAULT_DECISION_MODEL = "Gemini"
