import re
with open('pyproject.toml', 'r') as f:
    content = f.read()
content = content.replace('--cov-fail-under=80', '--cov-fail-under=85')
content = content.replace('fail_under = 80', 'fail_under = 85')
with open('pyproject.toml', 'w') as f:
    f.write(content)
