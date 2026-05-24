with open("tests/test_remove.py", "r") as f:
    content = f.read()

content = content.replace("registry.clear()\n        registry.update(reg)", "registry.clear()\n        registry.update(reg)")

# The logic of `perform_remove` is:
# registry = load_registry()
# if email in registry:
#     del registry[email]
#     save_registry(registry)

# If registry is already updated by python dict reference, and we update it again with the same dictionary after clearing it.
# Actually, the actual application does `del registry[email]` which mutates the dictionary, then saves it.
# Let's fix test_remove.py.
new_test_remove = """from pathlib import Path
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
        pass # The dictionary is mutated directly.
    monkeypatch.setattr(antigravity_manager.remove, "save_registry", mock_save)

    args = DummyArgs("user@example.com", str(b), yes=True)
    res = perform_remove(args)
    assert res["local_registry_removed"] is True
    assert len(res["local_files_removed"]) == 1
    assert "user@example.com" not in registry
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
    f.write(new_test_remove)
