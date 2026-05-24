import tarfile
from pathlib import Path
from antigravity_manager.profile import export_profile, import_profile
from antigravity_manager.config import AGM_HOME

def test_export_import_profile(tmp_path, monkeypatch):
    test_home = tmp_path / "antigravity_manager"
    test_home.mkdir()
    (test_home / "test.txt").write_text("dummy")

    monkeypatch.setattr("antigravity_manager.profile.AGM_HOME", test_home)

    export_path = tmp_path / "export.tar.gz"
    export_profile(export_path)

    assert export_path.exists()

    # modify home
    (test_home / "test.txt").write_text("modified")

    import_profile(export_path)

    assert (test_home / "test.txt").read_text() == "dummy"
    assert (tmp_path / "antigravity_manager.bak").exists()
