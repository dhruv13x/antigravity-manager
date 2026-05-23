from datetime import datetime

from antigravity_manager.cooldown import evaluate_metadata


def test_evaluate_metadata_uses_decision_model_not_any_model() -> None:
    metadata = {
        "email": "person@example.com",
        "plan": "Google AI Pro",
        "status": {
            "models": [
                {
                    "model_name": "Gemini 3.5 Flash (High)",
                    "is_available": False,
                    "refresh_at": "2026-05-22T23:00:00+05:30",
                },
                {"model_name": "B", "is_available": True, "refresh_at": None},
            ]
        },
    }

    status = evaluate_metadata(
        metadata,
        source="test",
        now=datetime.fromisoformat("2026-05-22T21:00:00+05:30"),
    )

    assert status.status == "cooldown"
    assert status.remaining_seconds == 7200
    assert status.available_models == 1
    assert status.total_models == 2


def test_evaluate_metadata_all_ready() -> None:
    metadata = {
        "email": "ready@example.com",
        "plan": "Google AI Pro",
        "status": {
            "models": [
                {
                    "model_name": "Gemini 3.5 Flash (High)",
                    "is_available": True,
                    "refresh_at": None,
                }
            ]
        },
    }

    status = evaluate_metadata(
        metadata,
        source="test",
        now=datetime.fromisoformat("2026-05-22T21:00:00+05:30"),
    )

    assert status.status == "ready"
    assert status.remaining_seconds == 0
    assert status.available_models == 1


def test_evaluate_metadata_missing_status() -> None:
    metadata = {
        "email": "missing@example.com",
    }
    status = evaluate_metadata(
        metadata,
        source="test",
        now=datetime.fromisoformat("2026-05-22T21:00:00+05:30"),
    )
    assert status.status == "ready"


def test_evaluate_metadata_multiple_models_all_ready() -> None:
    metadata = {
        "email": "test@example.com",
        "plan": "Google AI Pro",
        "status": {
            "models": [
                {
                    "model_name": "A",
                    "is_available": True,
                    "refresh_at": None,
                },
                {
                    "model_name": "B",
                    "is_available": True,
                    "refresh_at": None,
                },
            ]
        },
    }
    status = evaluate_metadata(
        metadata,
        source="test",
        now=datetime.fromisoformat("2026-05-22T21:00:00+05:30"),
    )
    assert status.status == "ready"
