import re

with open('src/antigravity_manager/restore.py', 'r') as f:
    content = f.read()

new_impl = '''
def restore_result_to_text(
    archive_path: Path,
    metadata: dict[str, Any],
    restored_files: list[Path],
    safety_path: Path | None,
    *,
    dry_run: bool,
    full: bool,
) -> "Panel":
    from .ui import Panel, Table, Tree, Group, Text

    title = "[warning]Restore Result (Dry Run)[/]" if dry_run else "[success]Restore Completed[/]"
    border_style = "warning" if dry_run else "success"

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", justify="right")
    table.add_column(style="white")

    table.add_row("Email:", str(metadata.get('email', 'unknown')))
    table.add_row("Plan:", str(metadata.get('plan', 'unknown')))
    table.add_row("Type:", "Full Restore" if full else "Auth-only Restore")
    table.add_row("Archive:", str(archive_path))

    if safety_path:
        table.add_row("Safety Backup:", f"[dim]{safety_path}[/dim]")

    components = [table]

    if restored_files:
        tree = Tree(f"📁 [bold bright_cyan]Restored Files[/]")
        for path in restored_files:
            tree.add(f"[green]{path}[/]")

        components.append(Text(""))
        components.append(tree)

    return Panel(
        Group(*components),
        title=title,
        border_style=border_style,
        expand=False
    )
'''

content = re.sub(r'def restore_result_to_text\(.*?\n\).*?:\n.*?(?=\n\n|\Z)', new_impl.strip(), content, flags=re.DOTALL)

with open('src/antigravity_manager/restore.py', 'w') as f:
    f.write(content)
