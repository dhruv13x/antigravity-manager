from pathlib import Path
from antigravity_manager.purge import perform_purge, purge_result_to_text

class DummyArgs:
    def __init__(self, source_dir, yes=False, dry_run=False):
        self.source_dir = source_dir
        self.yes = yes
        self.dry_run = dry_run

def test_perform_purge(tmp_path):
    d = tmp_path / "antigravity"
    d.mkdir()
    (d / "test.txt").write_text("hello")
    args = DummyArgs(str(d), yes=True)
    assert perform_purge(args) is True
    assert not d.exists()

def test_purge_result_to_text():
    out = purge_result_to_text(True, Path("/tmp"), False)
    assert "purged" in out
    assert "Antigravity home has been factory reset." in out
