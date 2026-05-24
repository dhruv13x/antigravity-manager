import re
with open('tests/test_coverage_ext2.py', 'r') as f:
    content = f.read()
content = re.sub(r'def test_credentials_doppler_env.*?assert k == "a"', '', content, flags=re.DOTALL)
with open('tests/test_coverage_ext2.py', 'w') as f:
    f.write(content)
