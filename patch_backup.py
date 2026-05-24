import re

with open('src/antigravity_manager/backup.py', 'r') as f:
    content = f.read()

new_impl = '''
def backup_result_to_text(
    archive_path: Path, metadata_path: Path, metadata: dict[str, Any], *, dry_run: bool
) -> "Panel":
    from .ui import Panel, Table, Group, Text, Tree

    title = "[warning]Backup Result (Dry Run)[/]" if dry_run else "[success]Backup Created[/]"
    border_style = "warning" if dry_run else "success"

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", justify="right")
    table.add_column(style="white")

    table.add_row("Email:", str(metadata.get('email', 'unknown')))
    table.add_row("Plan:", str(metadata.get('plan', 'unknown')))
    table.add_row("Archive:", str(archive_path))
    table.add_row("Metadata:", str(metadata_path))
    table.add_row("Next Available:", str(metadata.get('next_available_at', 'unknown')))

    anchor_src = metadata.get('backup_anchor_source', 'unknown')
    table.add_row("Anchor:", f"{metadata.get('backup_anchor_at', 'unknown')} [dim]({anchor_src})[/dim]")
    table.add_row("Mode:", str(metadata.get('backup_mode', 'unknown')))

    return Panel(
        table,
        title=title,
        border_style=border_style,
        expand=False
    )
'''

content = re.sub(r'def backup_result_to_text\(.*?\n\).*?:\n.*?(?=\n\n|\Z)', new_impl.strip(), content, flags=re.DOTALL)

# Add type ignore since we are returning Panel now
content = content.replace('def backup_result_to_text(', 'def backup_result_to_text(')

with open('src/antigravity_manager/backup.py', 'w') as f:
    f.write(content)
