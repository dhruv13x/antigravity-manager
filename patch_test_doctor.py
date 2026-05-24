import re
with open('tests/test_doctor_2.py', 'r') as f:
    content = f.read()

# Mock out resolve_credentials properly in test_run_doctor_pass
content = content.replace(
    'import shutil',
    'import shutil\n    monkeypatch.setattr("antigravity_manager.doctor.resolve_credentials", lambda *a, **kw: ("key", "secret", "b", "url"))\n    monkeypatch.setattr("antigravity_manager.doctor.verify_cloud_connectivity", lambda *a, **kw: True)'
)

with open('tests/test_doctor_2.py', 'w') as f:
    f.write(content)
