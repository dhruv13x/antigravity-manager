from __future__ import annotations

from datetime import datetime

from antigravity_manager.status import parse_live_status_text


SAMPLE_USAGE = """
drewpoul13x@gmail.com (Google AI Pro)

Model Quota

Gemini 3.5 Flash (High)
████████████████████ 100%
Quota available

Claude Sonnet 4.6 (Thinking)
░░░░░░░░░░░░░░░░░░░░ 0%
Refreshes in 2h 5m
"""


def test_parse_live_status_text_extracts_models_and_refresh() -> None:
    now = datetime.fromisoformat("2026-05-22T21:06:01+05:30")
    status = parse_live_status_text(SAMPLE_USAGE, now=now)

    assert status.email == "drewpoul13x@gmail.com"
    assert status.plan == "Google AI Pro"
    assert status.is_pro is True
    assert len(status.models) == 2
    assert status.models[0].model_name == "Gemini 3.5 Flash (High)"
    assert status.models[0].is_available is True
    assert status.models[1].quota_percent_left == 0
    assert status.models[1].refresh_at == datetime.fromisoformat("2026-05-22T23:11:01+05:30")
