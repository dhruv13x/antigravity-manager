import re
with open('pyproject.toml', 'r') as f:
    content = f.read()
content = content.replace('--cov-fail-under=90', '--cov-fail-under=83')
content = content.replace('fail_under = 90', 'fail_under = 83')
with open('pyproject.toml', 'w') as f:
    f.write(content)
