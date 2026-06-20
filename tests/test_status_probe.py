from datetime import datetime, timezone
from antigravity_manager.status import parse_live_status_text

def test_parse_probe_fallback():
    # Simulate a stuck /usage followed by a successful probe
    stuck_output = """
===== STARTUP =====
Account: embracedweapon@gmail.com (Standard)
> 
===== USAGE =====
USAGE TIMEOUT
===== PROBE =====
> hi
⚠ You have exhausted your capacity on this model. Your quota will reset after 121h36m11s.
"""
    now = datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
    status = parse_live_status_text(stuck_output, now=now)
    
    assert status.email == "embracedweapon@gmail.com"
    # Verify extraction from banner/footer without headers
    banner_footer_layout = stuck_output + """
▄▀▀▄        Antigravity CLI 1.0.8
     ▀▀▀▀▀▀       embracedweapon@gmail.com
    ▀▀▀▀▀▀▀▀      Claude Sonnet 4.6 (Thinking)
"""
    status = parse_live_status_text(banner_footer_layout, now=now)
    assert len(status.models) == 1
    # Formatting now wraps in group name for better sorting/rec
    assert "CLAUDE AND GPT MODELS" in status.models[0].model_name
    assert "Claude Sonnet 4.6 (Thinking)" in status.models[0].model_name
    assert status.models[0].quota_percent_left == 0
    assert "121h" in status.models[0].refresh_in_text

    # Verify extraction from footer
    footer_layout = stuck_output + """
esc to cancel                                           Gemini 3.5 Flash (High) · 
"""
    status = parse_live_status_text(footer_layout, now=now)
    assert len(status.models) == 1
    assert "GEMINI MODELS" in status.models[0].model_name
    assert "Gemini 3.5 Flash (High)" in status.models[0].model_name


def test_parse_probe_license_failure_blocks_account():
    stuck_output = """
===== STARTUP =====
Account: drdpsbose030@gmail.com
▄▀▀▄        Antigravity CLI 1.0.10
     ▀▀▀▀▀▀       drdpsbose030@gmail.com
    ▀▀▀▀▀▀▀▀      Claude Sonnet 4.6 (Thinking)
> 
===== USAGE =====
USAGE TIMEOUT
===== PROBE =====
> hi
⚠ You do not have a valid license of this product. Please contact your administrator to request a
license. If you are not an enterprise user and believe you are receiving this message as an error,
please try using the latest version and logging in again. (#3501)
"""
    now = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)
    status = parse_live_status_text(stuck_output, now=now)

    assert len(status.models) == 1
    assert "CLAUDE AND GPT MODELS" in status.models[0].model_name
    assert status.models[0].quota_percent_left is None
    assert status.models[0].is_available is False
    assert status.models[0].block_reason == "No valid Antigravity license"
    assert status.models[0].refresh_in_text == "Blocked: no valid license"


def test_license_failure_overrides_stale_usage_quota():
    output = """
===== STARTUP =====
Account: drdpsbose030@gmail.com
Claude Sonnet 4.6 (Thinking)
===== USAGE =====
Models & Quota
Claude Sonnet 4.6 (Thinking)
████████████████████ 100%
Quota available
===== PROBE =====
> hi
⚠ You do not have a valid license of this product. (#3501)
"""
    status = parse_live_status_text(output, now=datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc))

    assert len(status.models) == 1
    assert status.models[0].quota_percent_left is None
    assert status.models[0].is_available is False
    assert status.models[0].block_reason == "No valid Antigravity license"

if __name__ == "__main__":
    test_parse_probe_fallback()
