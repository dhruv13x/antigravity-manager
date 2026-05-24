import json
from datetime import datetime, timedelta

from antigravity_manager.cooldown import (
    ModelCooldown,
    evaluate_model,
    find_decision_model,
    format_remaining,
    read_active_email,
)


def test_format_remaining():
    assert format_remaining(0) == "now"
    assert format_remaining(60) == "1m"
    assert format_remaining(3660) == "1h 1m"
    assert format_remaining(90060) == "1d 1h 1m"


def test_evaluate_model():
    now = datetime.now()
    m = evaluate_model(
        {
            "model_name": "x",
            "quota_percent_left": 100,
            "is_available": True,
            "refresh_at": str(now + timedelta(seconds=10)),
        },
        now=now,
    )
    assert m.name == "x"
    assert m.is_available is True
    assert m.remaining_seconds == 0


def test_find_decision_model():
    m1 = ModelCooldown("gemini 3.5 flash (low)", 100, True, None, 0)
    m2 = ModelCooldown("gemini 3.5 flash (high)", 100, True, None, 0)
    assert find_decision_model((m1, m2), "gemini 3.5 flash") == m2


def test_read_active_email(tmp_path):
    (tmp_path / "google_accounts.json").write_text(json.dumps({"active": " user "}))
    assert read_active_email(tmp_path) == "user"
