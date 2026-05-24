import re

with open('src/antigravity_manager/remove.py', 'r') as f:
    content = f.read()

# restore the original signature list of tuples for remove.py results
new_impl = '''
def remove_result_to_text(results: list[tuple[str, Path | str, bool]], *, email: str, dry_run: bool) -> "Panel":
    from .ui import Panel, Tree

    if not results:
        return Panel(
            f"[yellow]No removal actions taken for {email}.[/]",
            title="[warning]Remove Aborted[/]",
            border_style="yellow",
            expand=False
        )

    title = f"[warning]Remove Plan for {email} (Dry Run)[/]" if dry_run else f"[danger]Account Removed: {email}[/]"
    border_style = "warning" if dry_run else "danger"

    tree = Tree(f"🗑️  [bold red]Traces Removed for {email}[/]")
    for category, path, removed in results:
        status_icon = "✅" if removed else ("⏭️ " if dry_run else "❌")
        tree.add(f"{status_icon} [bold]{category}[/]: {path}")

    return Panel(
        tree,
        title=title,
        border_style=border_style,
        expand=False
    )
'''
content = re.sub(r'def remove_result_to_text\(.*?\n\).*?:\n.*?(?=\n\n|\Z)', new_impl.strip(), content, flags=re.DOTALL)
with open('src/antigravity_manager/remove.py', 'w') as f:
    f.write(content)

with open('tests/test_ui_rendering.py', 'r') as f:
    content = f.read()

content = content.replace('panel = remove_result_to_text({"local_files_removed": [Path("/path")], "registry_removed": True}, email="a@b.c", dry_run=False)', 'panel = remove_result_to_text([("Cat", Path("/path"), True)], email="a@b.c", dry_run=False)')
content = content.replace('panel = remove_result_to_text({}, email="a@b.c", dry_run=True)', 'panel = remove_result_to_text([], email="a@b.c", dry_run=True)')

with open('tests/test_ui_rendering.py', 'w') as f:
    f.write(content)
