from antigravity_manager.status import (
    capture_tmux_status_text,
    wait_for_prompt,
    wait_for_usage_panel,
)


def test_capture_tmux_status_text(monkeypatch):
    monkeypatch.setattr("antigravity_manager.status.verify_tmux_available", lambda: None)

    import subprocess

    def mock_run(cmd, *a, **kw):
        class CP:
            returncode = 0
            stdout = ""

        return CP()

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr("antigravity_manager.status.wait_for_prompt", lambda *a, **kw: None)
    monkeypatch.setattr(
        "antigravity_manager.status.wait_for_usage_panel", lambda *a, **kw: "Mock Panel Text"
    )

    # We must mock run_command to return an object with a stdout property containing `%begin`
    def mock_rc(cmd, *a, **kw):
        class CP:
            returncode = 0
            stdout = "%begin 12345"

        return CP()

    monkeypatch.setattr("antigravity_manager.status.run_command", mock_rc)

    out = capture_tmux_status_text()
    assert "Mock Panel Text" in out


def test_wait_for_prompt(monkeypatch):
    import time

    monkeypatch.setattr(time, "sleep", lambda x: None)
    monkeypatch.setattr(
        "antigravity_manager.status.capture_pane", lambda x: "user@example.com (pro)\n> "
    )
    wait_for_prompt("pane", timeout_seconds=1)


def test_wait_for_usage_panel(monkeypatch):
    import time

    monkeypatch.setattr(time, "sleep", lambda x: None)
    monkeypatch.setattr(
        "antigravity_manager.status.capture_pane",
        lambda x: "Model Quota\nuser@example.com (pro)\n(Gemini 3.5 Flash)\n  Quota: 50%\n",
    )
    out = wait_for_usage_panel("pane", timeout_seconds=1)
    assert "Model Quota" in out
