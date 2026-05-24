import re

# Patch prune.py
with open('src/antigravity_manager/prune.py', 'r') as f:
    content = f.read()

new_impl = '''
def prune_result_to_text(plan: PrunePlan, *, dry_run: bool, source_dir: Path | None = None) -> "Panel":
    from .ui import Panel, Table, Tree, Group, Text

    title = "[warning]Prune Plan (Dry Run)[/]" if dry_run else "[success]Prune Completed[/]"
    border_style = "warning" if dry_run else "success"

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", justify="right")
    table.add_column(style="white")

    table.add_row("Mode:", "dry-run" if dry_run else "pruned")
    if source_dir:
        table.add_row("Source Dir:", str(source_dir))
    table.add_row("Status:", "preserved authentication and persistent state")

    components = [table]

    if plan.files or plan.directories:
        components.append(Text(""))
        tree = Tree("🗑️  [bold red]Removed Items[/]")

        if plan.files:
            file_node = tree.add(f"[bold]Files ({len(plan.files)})[/]")
            for path in plan.files:
                file_node.add(f"[red]{path}[/]")

        if plan.directories:
            dir_node = tree.add(f"[bold]Directories ({len(plan.directories)})[/]")
            for path in plan.directories:
                dir_node.add(f"[red]{path}/[/]")

        components.append(tree)

    return Panel(
        Group(*components),
        title=title,
        border_style=border_style,
        expand=False
    )
'''
content = re.sub(r'def prune_result_to_text\(.*?\n\).*?:\n.*?(?=\n\n|\Z)', new_impl.strip(), content, flags=re.DOTALL)
with open('src/antigravity_manager/prune.py', 'w') as f:
    f.write(content)

# Patch purge.py
with open('src/antigravity_manager/purge.py', 'r') as f:
    content = f.read()

new_impl = '''
def purge_result_to_text(success: bool, *, source_dir: Path, dry_run: bool) -> "Panel":
    from .ui import Panel, Text

    if not success:
        return Panel(
            "[yellow]Purge aborted by user.[/]",
            title="[yellow]Purge Aborted[/]",
            border_style="yellow",
            expand=False
        )

    title = "[warning]Purge Plan (Dry Run)[/]" if dry_run else "[danger]Purge Completed[/]"
    border_style = "warning" if dry_run else "danger"

    msg = f"Would remove all Antigravity state at: [bold]{source_dir}[/]" if dry_run else f"Successfully removed all Antigravity state at: [bold]{source_dir}[/]"

    return Panel(
        Text.from_markup(msg),
        title=title,
        border_style=border_style,
        expand=False
    )
'''
content = re.sub(r'def purge_result_to_text\(.*?\n\).*?:\n.*?(?=\n\n|\Z)', new_impl.strip(), content, flags=re.DOTALL)
with open('src/antigravity_manager/purge.py', 'w') as f:
    f.write(content)

# Patch remove.py
with open('src/antigravity_manager/remove.py', 'r') as f:
    content = f.read()

new_impl = '''
def remove_result_to_text(results: list[tuple[str, Path | str, bool]], *, email: str, dry_run: bool) -> "Panel":
    from .ui import Panel, Tree, Group, Text

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
