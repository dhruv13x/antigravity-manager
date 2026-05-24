import re

with open('src/antigravity_manager/backup.py', 'r') as f:
    content = f.read()
content = content.replace('def backup_result_to_text(\n    archive_path: Path, metadata_path: Path, metadata: dict[str, Any], *, dry_run: bool\n) -> Panel:', 'def backup_result_to_text(\n    archive_path: Path, metadata_path: Path, metadata: dict[str, Any], *, dry_run: bool\n) -> Any:')
content = content.replace('console.print(f"Encrypting archive: {archive_path} -> .gpg")', 'import antigravity_manager.ui\n        antigravity_manager.ui.console.print(f"Encrypting archive: {archive_path} -> .gpg")')
content = content.replace('passphrase = os.environ.get("AGM_BACKUP_PASSWORD")', 'import os\n        passphrase = os.environ.get("AGM_BACKUP_PASSWORD")')
content = content.replace('raise RuntimeError(f"GPG encryption failed: {e}")', 'raise RuntimeError(f"GPG encryption failed: {e}") from e')
with open('src/antigravity_manager/backup.py', 'w') as f:
    f.write(content)


with open('src/antigravity_manager/credentials.py', 'r') as f:
    content = f.read()
content = content.replace('if c_id: updated = True', 'if c_id:\n                updated = True')
content = content.replace('if c_key: updated = True', 'if c_key:\n                updated = True')
content = content.replace('if c_bucket: updated = True', 'if c_bucket:\n                updated = True')
content = content.replace('if c_endpoint: updated = True', 'if c_endpoint:\n                updated = True')
with open('src/antigravity_manager/credentials.py', 'w') as f:
    f.write(content)

with open('src/antigravity_manager/doctor.py', 'r') as f:
    content = f.read()
content = content.replace('for name, path, detail in dirs:', 'for name, path, _ in dirs:')
with open('src/antigravity_manager/doctor.py', 'w') as f:
    f.write(content)

with open('src/antigravity_manager/remove.py', 'r') as f:
    content = f.read()
content = content.replace(') -> Panel:', ') -> Any:')
# remove trailing str code left behind by patching
content = re.sub(r'lines\.append\(f"local_files_removed.*?join\(lines\)', '', content, flags=re.DOTALL)
with open('src/antigravity_manager/remove.py', 'w') as f:
    f.write(content)

with open('src/antigravity_manager/restore.py', 'r') as f:
    content = f.read()
content = content.replace(') -> Panel:', ') -> Any:')
content = content.replace('passphrase = os.environ.get("AGM_BACKUP_PASSWORD")', 'import os\n            passphrase = os.environ.get("AGM_BACKUP_PASSWORD")')
content = content.replace('raise RuntimeError(f"GPG decryption failed: {e}")', 'raise RuntimeError(f"GPG decryption failed: {e}") from e')
with open('src/antigravity_manager/restore.py', 'w') as f:
    f.write(content)

with open('src/antigravity_manager/status.py', 'r') as f:
    content = f.read()
content = content.replace(') -> Panel:', ') -> Any:')
with open('src/antigravity_manager/status.py', 'w') as f:
    f.write(content)

with open('src/antigravity_manager/prune.py', 'r') as f:
    content = f.read()
content = content.replace(') -> Panel:', ') -> Any:')
content = content.replace('def prune_result_to_text(plan: PrunePlan, *, dry_run: bool, source_dir: Path | None = None) -> "Panel":', 'def prune_result_to_text(plan: PrunePlan, *, dry_run: bool, source_dir: Path | None = None) -> Any:')
with open('src/antigravity_manager/prune.py', 'w') as f:
    f.write(content)

with open('src/antigravity_manager/purge.py', 'r') as f:
    content = f.read()
content = content.replace(') -> Panel:', ') -> Any:')
content = content.replace('def purge_result_to_text(success: bool, *, source_dir: Path, dry_run: bool) -> "Panel":', 'def purge_result_to_text(success: bool, *, source_dir: Path, dry_run: bool) -> Any:')
with open('src/antigravity_manager/purge.py', 'w') as f:
    f.write(content)
