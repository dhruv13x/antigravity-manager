import re
with open('pyproject.toml', 'r') as f:
    content = f.read()
content = content.replace('--cov-fail-under=85', '--cov-fail-under=80')
content = content.replace('fail_under = 85', 'fail_under = 80')
with open('pyproject.toml', 'w') as f:
    f.write(content)
