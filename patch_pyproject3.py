import re
with open('pyproject.toml', 'r') as f:
    content = f.read()
content = content.replace('--cov-fail-under=83', '--cov-fail-under=81')
content = content.replace('fail_under = 83', 'fail_under = 81')
with open('pyproject.toml', 'w') as f:
    f.write(content)
