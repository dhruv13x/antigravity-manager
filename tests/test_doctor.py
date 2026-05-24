from antigravity_manager.doctor import run_doctor


def test_run_doctor_all_fail(tmp_path):
    checks = run_doctor(antigravity_home=tmp_path / "x", backup_dir=tmp_path / "z")
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
    assert run_doctor(antigravity_home=y, backup_dir=z)
