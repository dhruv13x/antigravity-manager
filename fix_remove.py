import re

with open('src/antigravity_manager/remove.py', 'r') as f:
    content = f.read()

new_impl = '''
def remove_result_to_text(results: dict[str, Any], email: str, dry_run: bool) -> "Panel":
    from .ui import Panel, Tree

    title = f"[warning]Remove Plan for {email} (Dry Run)[/]" if dry_run else f"[danger]Account Removed: {email}[/]"
    border_style = "warning" if dry_run else "danger"

    tree = Tree(f"🗑️  [bold red]Traces Removed for {email}[/]")

    if results.get("local_files_removed"):
        for path in results["local_files_removed"]:
            tree.add(f"✅ [bold]local file[/]: {path}")

    if results.get("local_registry_removed"):
        tree.add(f"✅ [bold]registry entry[/]: {email}")

    if not results.get("local_files_removed") and not results.get("local_registry_removed"):
        tree.add(f"[yellow]No removal actions taken for {email}.[/]")

    return Panel(
        tree,
        title=title,
        border_style=border_style,
        expand=False
    )
'''

content = re.sub(r'def remove_result_to_text\(results: dict\[str, Any\], email: str, dry_run: bool\) -> str:.*?(?=\Z|\n\n)', new_impl.strip(), content, flags=re.DOTALL)

with open('src/antigravity_manager/remove.py', 'w') as f:
    f.write(content)

with open('tests/test_ui_rendering.py', 'r') as f:
    content = f.read()

content = content.replace('panel = remove_result_to_text([("Cat", Path("/path"), True)], email="a@b.c", dry_run=False)', 'panel = remove_result_to_text({"local_files_removed": ["/path"], "local_registry_removed": True}, email="a@b.c", dry_run=False)')
content = content.replace('panel = remove_result_to_text([], email="a@b.c", dry_run=True)', 'panel = remove_result_to_text({}, email="a@b.c", dry_run=True)')

with open('tests/test_ui_rendering.py', 'w') as f:
    f.write(content)
