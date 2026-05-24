from antigravity_manager.doctor import run_doctor


def test_run_doctor_pass(tmp_path, monkeypatch):
    import shutil

    monkeypatch.setattr(
        "antigravity_manager.doctor.resolve_credentials",
        lambda *a, **kw: ("key", "secret", "b", "url"),
    )
    monkeypatch.setattr(
        "antigravity_manager.doctor.verify_cloud_connectivity", lambda *a, **kw: True
    )
    monkeypatch.setattr(shutil, "which", lambda x: "cmd")
    x = tmp_path / "x"
    x.mkdir()
    (x / "google_accounts.json").write_text("{}")
    (x / "oauth_creds.json").write_text("{}")
    (x / "state.json").write_text("{}")
    (x / "settings.json").write_text("{}")
    (x / "installation_id").write_text("1")

    y = tmp_path / "y"
    y.mkdir()
    (y / "antigravity-oauth-token").write_text("{}")
    (y / "installation_id").write_text("{}")
    (y / "settings.json").write_text("{}")
    (y / "keybindings.json").write_text("{}")

    z = tmp_path / "z"
    z.mkdir()

    checks = run_doctor(antigravity_home=y, gemini_home=x, backup_dir=z)
    assert all(ok for name, ok, desc in checks)
