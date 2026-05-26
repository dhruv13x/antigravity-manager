from __future__ import annotations

from datetime import datetime

from antigravity_manager.status import parse_live_status_text

SAMPLE_USAGE = """
user@example.com (Google AI Pro)

Model Quota

Gemini 3.5 Flash (High)
████████████████████ 100%
Quota available

Claude Sonnet 4.6 (Thinking)
░░░░░░░░░░░░░░░░░░░░ 0%
Refreshes in 2h 5m

Gemini 3.5 Flash (Medium)
███████████ ░░░░░░░░░░░ ░░░░░░░░░░░ ░░░░░░░░░░░ ░░░░░░░░░░░ 20%
20% remaining · Refreshes in 3h 22m
"""


def test_parse_live_status_text_extracts_models_and_refresh() -> None:
    now = datetime.fromisoformat("2026-05-22T21:06:01+05:30")
    status = parse_live_status_text(SAMPLE_USAGE, now=now)

    assert status.email == "user@example.com"
    assert status.plan == "Google AI Pro"
    assert status.is_pro is True
    assert len(status.models) == 3
    assert status.models[0].model_name == "Gemini 3.5 Flash (High)"
    assert status.models[0].is_available is True
    assert status.models[1].quota_percent_left == 0
    assert status.models[1].refresh_at == datetime.fromisoformat("2026-05-22T23:11:01+05:30")
    assert status.models[2].model_name == "Gemini 3.5 Flash (Medium)"
    assert status.models[2].quota_percent_left == 20
    assert status.models[2].is_available is False
    assert status.models[2].refresh_at == datetime.fromisoformat("2026-05-23T00:28:01+05:30")


def test_parse_email_and_plan_without_parentheses() -> None:
    from antigravity_manager.status import parse_email_and_plan

    text = "user@example.com\nGemini 3.5 Flash (High)"
    email, plan = parse_email_and_plan(text)
    assert email == "user@example.com"
    assert plan == "Standard"


def test_parse_email_and_plan_with_parentheses() -> None:
    from antigravity_manager.status import parse_email_and_plan

    text = "user@example.com (Pro Plan)\nGemini 3.5 Flash (High)"
    email, plan = parse_email_and_plan(text)
    assert email == "user@example.com"
    assert plan == "Pro Plan"


def test_wait_for_prompt_handles_trust_prompt() -> None:
    from unittest.mock import patch

    from antigravity_manager.status import wait_for_prompt

    with (
        patch("antigravity_manager.status.capture_pane") as mock_capture,
        patch("antigravity_manager.status.run_command") as mock_run,
        patch("time.sleep", return_value=None),
    ):
        # First call: show trust prompt
        # Second call: show email and prompt (logged in)
        # Succeed after 3 stable reads of the second output
        mock_capture.side_effect = [
            "Do you trust the contents of this project?",
            "user@example.com (Pro)\n>",
            "user@example.com (Pro)\n>",
            "user@example.com (Pro)\n>",
        ]

        output = wait_for_prompt("pane_123", timeout_seconds=10)

        assert "user@example.com" in output
        # Check that tmux send-keys Enter was called
        mock_run.assert_any_call(["tmux", "send-keys", "-t", "pane_123", "Enter"], check=False)
