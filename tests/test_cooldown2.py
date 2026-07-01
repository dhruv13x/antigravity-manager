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


def test_evaluate_entries_prefers_latest_status_metadata(monkeypatch):
    monkeypatch.setattr("antigravity_manager.cooldown.load_registry", lambda: {})
    backup = BackupEntry(
        Path("backup.tar.gz"),
        "user@example.com",
        "pro",
        "2024-01-01T00:00:00+00:00",
        "2024-01-01T00:00:00+00:00",
        "2024-01-01T12:00:00+00:00",
        "full",
        {
            "email": "user@example.com",
            "status": {
                "models": [
                    {
                        "model_name": "gemini 3.5 flash",
                        "is_available": False,
                        "refresh_at": "2024-01-01T12:00:00+00:00",
                    }
                ]
            },
        },
    )
    status_metadata = BackupEntry(
        Path("status.metadata.json"),
        "user@example.com",
        "pro",
        "2024-01-01T10:00:00+00:00",
        "2024-01-01T10:00:00+00:00",
        "2024-01-01T10:00:00+00:00",
        "status-only",
        {
            "email": "user@example.com",
            "status": {
                "models": [
                    {
                        "model_name": "gemini 3.5 flash",
                        "is_available": True,
                    }
                ]
            },
        },
        source="status",
    )

    statuses = evaluate_entries(
        [backup, status_metadata],
        now=datetime(2024, 1, 1, 10, tzinfo=UTC),
    )

    assert len(statuses) == 1
    assert statuses[0].source == "status"
    assert statuses[0].status == "ready"


def test_blocked_metadata_is_not_ready_and_sorts_after_cooldown(monkeypatch):
    monkeypatch.setattr("antigravity_manager.cooldown.load_registry", lambda: {})
    blocked = BackupEntry(
        Path("blocked.metadata.json"),
        "blocked@example.com",
        "standard",
        "2024-01-01T10:00:00+00:00",
        "2024-01-01T10:00:00+00:00",
        "2024-01-01T10:00:00+00:00",
        "status-only",
        {
            "email": "blocked@example.com",
            "captured_at": "2024-01-01T10:00:00+00:00",
            "status": {
                "models": [
                    {
                        "model_name": "CLAUDE AND GPT MODELS (Claude Sonnet 4.6 (Thinking))",
                        "quota_percent_left": None,
                        "is_available": False,
                        "block_reason": "No valid Antigravity license",
                    }
                ]
            },
        },
    )
    cooldown = BackupEntry(
        Path("cooldown.metadata.json"),
        "cooldown@example.com",
        "standard",
        "2024-01-01T10:00:00+00:00",
        "2024-01-01T10:00:00+00:00",
        "2024-01-01T11:00:00+00:00",
        "status-only",
        {
            "email": "cooldown@example.com",
            "captured_at": "2024-01-01T10:00:00+00:00",
            "status": {
                "models": [
                    {
                        "model_name": "gemini 3.5 flash",
                        "is_available": False,
                        "refresh_at": "2024-01-01T11:00:00+00:00",
                    }
                ]
            },
        },
    )

    statuses = evaluate_entries(
        [blocked, cooldown],
        now=datetime(2024, 1, 1, 10, tzinfo=UTC),
        decision_model="claude",
    )

    assert statuses[0].email == "cooldown@example.com"
    assert statuses[0].status == "cooldown"
    assert statuses[1].email == "blocked@example.com"
    assert statuses[1].status == "blocked"


def test_format_model_usage():
    m1 = ModelCooldown("a", 100, True, None, 0)
    assert "Ready" in format_model_usage(m1)
    assert "100%" in format_model_usage(m1)

    m2 = ModelCooldown("Gemini 3.5 Flash", None, False, None, 60)
    assert "Gemini" in format_model_usage(m2)
    assert "1m" in format_model_usage(m2)

    m3 = ModelCooldown("Gemini 3.5 Flash", 20, False, None, 11940)  # 3 hours and 19 minutes
    assert "Gemini" in format_model_usage(m3)
    assert "20%" in format_model_usage(m3)
    assert "3h19m" in format_model_usage(m3).replace(" ", "")


def test_evaluate_entries_sorting_by_last_checked(monkeypatch):
    monkeypatch.setattr("antigravity_manager.cooldown.load_registry", lambda: {})
    e1 = BackupEntry(
        Path("a"),
        "newer@example.com",
        "pro",
        "2024-01-01T11:00:00+00:00",
        "2024-01-01T11:00:00+00:00",
        "2024-01-01T11:00:00+00:00",
        "status-only",
        {"email": "newer@example.com", "captured_at": "2024-01-01T11:00:00+00:00", "status": {"models": []}},
    )
    e2 = BackupEntry(
        Path("b"),
        "older@example.com",
        "pro",
        "2024-01-01T10:00:00+00:00",
        "2024-01-01T10:00:00+00:00",
        "2024-01-01T10:00:00+00:00",
        "status-only",
        {"email": "older@example.com", "captured_at": "2024-01-01T10:00:00+00:00", "status": {"models": []}},
    )
    statuses = evaluate_entries(
        [e1, e2],
        now=datetime(2024, 1, 1, 12, tzinfo=UTC),
    )
    assert len(statuses) == 2
    assert statuses[0].email == "older@example.com"
    assert statuses[1].email == "newer@example.com"


def test_group_models_separates_families():
    from antigravity_manager.cooldown import group_models
    m1 = ModelCooldown("GEMINI MODELS (Gemini 3.1 Pro (High))", 98, False, None, 3600)
    m2 = ModelCooldown("CLAUDE AND GPT MODELS (Claude Opus 4.6 (Thinking))", 98, False, None, 3600)
    
    grouped = group_models((m1, m2))
    assert len(grouped) == 2
    assert grouped[0] == m1
    assert grouped[1] == m2

