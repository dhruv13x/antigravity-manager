with open('src/antigravity_manager/backup.py', 'r') as f:
    content = f.read()
if 'from .ui import console' not in content:
    content = content.replace('from .ui import', 'from .ui import console,')
with open('src/antigravity_manager/backup.py', 'w') as f:
    f.write(content)
