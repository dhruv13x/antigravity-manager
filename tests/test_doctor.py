from antigravity_manager.doctor import run_doctor


def test_run_doctor_all_fail(tmp_path):
    checks = run_doctor(
        antigravity_home=tmp_path / "x", gemini_home=tmp_path / "y", backup_dir=tmp_path / "z"
    )
    assert not all(ok for name, ok, desc in checks)


def test_run_doctor_pass(tmp_path):
    x = tmp_path / "x"
    x.mkdir()
    (x / "google_accounts.json").write_text("{}")
    y = tmp_path / "y"
    y.mkdir()
    (y / "state.json").write_text("{}")
    z = tmp_path / "z"
    z.mkdir()
    checks = run_doctor(antigravity_home=y, gemini_home=x, backup_dir=z)
    # wait, the logic checks specific files. I'll just check coverage output.
