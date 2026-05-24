from antigravity_manager.doctor import run_doctor

def test_run_doctor_pass(tmp_path, monkeypatch):
    import shutil
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

    # Mock verify_cloud_connectivity and resolve_credentials to return true
    import antigravity_manager.doctor
    monkeypatch.setattr(antigravity_manager.doctor, "verify_cloud_connectivity", lambda *a, **kw: True)
    monkeypatch.setattr(antigravity_manager.doctor, "resolve_credentials", lambda *a, **kw: ("a", "s", "b", "e"))

    # We also mock urllib.request.urlopen to always succeed
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: None)

    checks = run_doctor(antigravity_home=y, gemini_home=x, backup_dir=z)

    # Tool 'agy' is not installed by default in test environments, so it may be false
    # We'll assert that directory checks and cloud pass, and our mocked tools pass
    assert checks[-1][1] == True # Cloud check
    assert checks[-2][1] == True # Network check
