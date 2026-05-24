from datetime import UTC, datetime
from pathlib import Path

from antigravity_manager.cooldown import (
    ModelCooldown,
    evaluate_entries,
    evaluate_metadata,
    format_model_usage,
)
from antigravity_manager.list_backups import BackupEntry


def test_evaluate_metadata():
    m = {
        "status": {
            "models": [
                {"model_name": "x", "is_available": True},
                {
                    "model_name": "gemini 3.5 flash",
                    "is_available": False,
                    "refresh_at": "2024-01-01T12:00:00+00:00",
                },
            ]
        },
        "email": "user",
    }
    st = evaluate_metadata(m, source="test", now=datetime(2024, 1, 1, 10, tzinfo=UTC))
    assert st.email == "user"
    assert st.available_models == 1
    assert st.total_models == 2


def test_evaluate_entries(monkeypatch):
    e1 = BackupEntry(
        Path("a"),
        "user",
        "pro",
        "now",
        "now",
        "now",
        "mode",
        {"email": "user", "status": {"models": []}},
    )
    e2 = BackupEntry(
        Path("b"),
        "other",
        "pro",
        "now",
        "now",
        "now",
        "mode",
        {"email": "other", "status": {"models": []}},
    )
    statuses = evaluate_entries([e1, e2])
    # evaluate_entries also reads the registry inside
    assert len(statuses) >= 2


def test_format_model_usage():
    m1 = ModelCooldown("a", 100, True, None, 0)
    assert "Ready" in format_model_usage(m1)
    assert "100%" in format_model_usage(m1)

    m2 = ModelCooldown("Gemini 3.5 Flash", None, False, None, 60)
    assert "G3.5F" in format_model_usage(m2)
    assert "1m" in format_model_usage(m2)
