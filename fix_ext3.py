import re

with open('tests/test_coverage_ext3.py', 'r') as f:
    content = f.read()

# Fix mock issues
content = content.replace(
    'monkeypatch.setattr("antigravity_manager.cli.perform_remove", lambda args: [])',
    'monkeypatch.setattr("antigravity_manager.cli.perform_remove", lambda args: {"local_files_removed": [], "local_registry_removed": False})'
)
content = content.replace(
    'monkeypatch.setattr("antigravity_manager.cli.perform_prune", lambda *a, **k: PrunePlan())',
    'monkeypatch.setattr("antigravity_manager.cli.perform_prune", lambda *a, **k: type("PrunePlan", (), {"files": [], "directories": []})())'
)

with open('tests/test_coverage_ext3.py', 'w') as f:
    f.write(content)
