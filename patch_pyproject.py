import re

with open('pyproject.toml', 'r') as f:
    content = f.read()

content = content.replace('--cov-fail-under=50', '--cov-fail-under=90')
content = content.replace('fail_under = 50', 'fail_under = 90')

with open('pyproject.toml', 'w') as f:
    f.write(content)
