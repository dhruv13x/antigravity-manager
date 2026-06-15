from antigravity_manager.status import verify_tmux_available, capture_pane, wait_for_prompt, wait_for_usage_panel, capture_tmux_status_text, AntigravityStatusError, parse_model_blocks, LiveStatus, parse_live_status_text
import pytest

def test_verify_tmux_available(monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: None)
    verify_tmux_available()

    def raise_err(*a, **kw):
        raise FileNotFoundError()
    monkeypatch.setattr(subprocess, "run", raise_err)
    with pytest.raises(AntigravityStatusError):
        verify_tmux_available()

def test_parse_model_blocks():
    from datetime import datetime
    text = "(Gemini 3.5 Flash)\n  Quota: 50%\n  Refreshes in 1h 2m"
    blocks = parse_model_blocks(text, now=datetime.now())
    assert len(blocks) > 0

def test_parse_live_status_text():
    from datetime import datetime
    text = "user@example.com (pro)\nModel Quota\n(Gemini 3.5 Flash)\n  Quota: 50%\n  Refreshes in 1h 2m"
    now = datetime(2024, 1, 1, 10)
    st = parse_live_status_text(text, now=now)
    assert st.email == "user@example.com"
    assert st.plan == "pro"
    assert st.is_pro is True
    assert len(st.models) == 1
    assert "GEMINI MODELS" in st.models[0].model_name
    assert "(Gemini 3.5 Flash)" in st.models[0].model_name
