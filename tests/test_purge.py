from pathlib import Path
from antigravity_manager.purge import perform_purge, purge_result_to_text

class DummyArgs:
    def __init__(self, source_dir, yes=False, dry_run=False):
        self.source_dir = source_dir
        self.yes = yes
        self.dry_run = dry_run

def test_perform_purge(tmp_path, monkeypatch):
    d = tmp_path / "antigravity"
    d.mkdir()
    (d / "test.txt").write_text("hello")
    safety_dir = tmp_path / "safety"
    monkeypatch.setattr("antigravity_manager.purge.SAFETY_BACKUP_DIR", safety_dir)
    args = DummyArgs(str(d), yes=True)
    assert perform_purge(args) is True
    assert not d.exists()
    assert any(path.name.endswith("-unknown-pre-purge-antigravity") for path in safety_dir.iterdir())

def test_purge_result_to_text():
    out = purge_result_to_text(True, Path("/tmp"), False)
    assert "purged" in out
    assert "Antigravity home has been factory reset." in out
