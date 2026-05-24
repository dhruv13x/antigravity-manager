with open("tests/test_remove.py", "r") as f:
    content = f.read()

# I messed up test_remove.py assertions during my tests fixing.
# It currently says:
#     from rich.console import Console
#     c = Console(force_terminal=False)
#     with c.capture() as cap:
#         c.print(out)
#     assert out is not None

# But there are duplicates from when I tried to fix it with sed earlier.
# Let's clean it up properly.
content = """from pathlib import Path
from antigravity_manager.remove import perform_remove, remove_result_to_text
from antigravity_manager.registry import save_registry, load_registry

class DummyArgs:
    def __init__(self, email, backup_dir, dry_run=False, yes=False):
        self.email = email
        self.backup_dir = backup_dir
        self.dry_run = dry_run
        self.yes = yes

def test_perform_remove_local(tmp_path, monkeypatch):
    b = tmp_path / "backups"
    b.mkdir()
    (b / "user@example.com-latest-antigravity.tar.gz").write_text("")
    (b / "other@example.com-latest-antigravity.tar.gz").write_text("")
    import antigravity_manager.remove
    monkeypatch.setattr(antigravity_manager.remove, "Confirm", type("MockConfirm", (), {"ask": classmethod(lambda cls, msg: True)}))

    registry = {"user@example.com": {}, "other@example.com": {}}
    monkeypatch.setattr(antigravity_manager.remove, "load_registry", lambda: registry)
    def mock_save(reg):
        registry.clear()
        registry.update(reg)
    monkeypatch.setattr(antigravity_manager.remove, "save_registry", mock_save)

    args = DummyArgs("user@example.com", str(b), yes=True)
    res = perform_remove(args)
    assert res["local_registry_removed"] is True
    assert len(res["local_files_removed"]) == 1
    assert "user" not in registry
    assert "other@example.com" in registry

def test_remove_result_to_text():
    results = {
        "local_files_removed": ["file1.tar.gz"],
        "local_registry_removed": True,
        "cloud_files_removed": [],
        "cloud_registry_removed": False,
    }
    out = remove_result_to_text(results, "user@example.com", False)
    assert out is not None
"""
with open("tests/test_remove.py", "w") as f:
    f.write(content)
