from pathlib import Path

from antigravity_manager.purge import perform_purge, purge_result_to_text


class DummyArgs:
    def __init__(
        self, source_dir, yes=False, dry_run=False, gemini_config_dir=None, session_dir=None
    ):
        self.source_dir = source_dir
        self.yes = yes
        self.dry_run = dry_run
        self.gemini_config_dir = gemini_config_dir
        self.session_dir = session_dir


def test_perform_purge(tmp_path, monkeypatch):
    d = tmp_path / "antigravity"
    d.mkdir()
    (d / "test.txt").write_text("hello")
    safety_dir = tmp_path / "safety"
    monkeypatch.setattr("antigravity_manager.purge.SAFETY_BACKUP_DIR", safety_dir)
    args = DummyArgs(str(d), yes=True)
    assert perform_purge(args) is True
    assert not d.exists()
    assert any(
        path.name.endswith("-unknown-pre-purge-antigravity.tar.gz")
        for path in safety_dir.iterdir()
    )


def test_purge_result_to_text():
    out = purge_result_to_text(True, Path("/tmp"), False)
    assert "purged" in out
    assert "Antigravity home has been factory reset." in out


def test_perform_purge_removes_session_config_dirs(tmp_path, monkeypatch):
    source_dir = tmp_path / "antigravity"
    source_dir.mkdir()
    (source_dir / "test.txt").write_text("hello")

    gemini_config_dir = tmp_path / "gemini" / "config"
    gemini_config_dir.mkdir(parents=True)
    (gemini_config_dir / "projects").mkdir()
    (gemini_config_dir / "projects" / "project.json").touch()

    session_dir = tmp_path / ".antigravitycli"
    session_dir.mkdir()
    (session_dir / "project.json").symlink_to(gemini_config_dir / "projects" / "project.json")

    safety_dir = tmp_path / "safety"
    monkeypatch.setattr("antigravity_manager.purge.SAFETY_BACKUP_DIR", safety_dir)

    args = DummyArgs(
        str(source_dir),
        yes=True,
        gemini_config_dir=str(gemini_config_dir),
        session_dir=str(session_dir),
    )
    assert perform_purge(args) is True

    assert not source_dir.exists()
    assert not gemini_config_dir.exists()
    assert not session_dir.exists()
