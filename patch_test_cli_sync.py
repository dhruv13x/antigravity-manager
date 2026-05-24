import re

with open('tests/test_cli_commands.py', 'r') as f:
    content = f.read()

# Fix resolve_credentials in tests to mock correctly
content = content.replace(
    'import antigravity_manager.cli',
    'import antigravity_manager.cli\n    monkeypatch.setattr("antigravity_manager.cli.resolve_credentials", lambda *a, **kw: ("key", "secret", "b", "url"))'
)

with open('tests/test_cli_commands.py', 'w') as f:
    f.write(content)
