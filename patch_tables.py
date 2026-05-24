import re

# Refactor list_backups.py
with open('src/antigravity_manager/list_backups.py', 'r') as f:
    content = f.read()

new_impl = '''
def print_entries_table(entries: list[BackupEntry]) -> None:
    from .ui import Panel, Table, console

    if not entries:
        console.print(Panel("[warning]No backups found.[/]", title="[bold]Backups[/]", border_style="warning", expand=False))
        return

    table = Table(show_header=True, header_style="bold bright_magenta", box=None, padding=(0, 2))
    table.add_column("Archive", style="bold bright_cyan")
    table.add_column("Email", style="bright_green")
    table.add_column("Plan")
    table.add_column("Mode", justify="center")
    table.add_column("Captured", justify="right", style="dim")
    table.add_column("Next Available", justify="right", style="bold bright_yellow")

    for entry in entries:
        table.add_row(
            entry.archive_path.name,
            entry.email,
            entry.plan,
            entry.backup_mode,
            entry.captured_at,
            entry.next_available_at,
        )
    console.print(
        Panel(table, title="[success]Available Backups[/]", border_style="success", expand=False)
    )
'''
content = re.sub(r'def print_entries_table\(.*?\n\).*?expand=False,\n    \)', new_impl.strip(), content, flags=re.DOTALL)
with open('src/antigravity_manager/list_backups.py', 'w') as f:
    f.write(content)

# Refactor cooldown.py
with open('src/antigravity_manager/cooldown.py', 'r') as f:
    content = f.read()

new_impl = '''
def print_statuses_table(statuses: list[CooldownStatus]) -> None:
    from .ui import Panel, Table, console

    if not statuses:
        console.print(Panel("[warning]No account statuses found.[/]", title="[bold]Cooldown Status[/]", border_style="warning", expand=False))
        return

    active_email = read_active_email()
    table = Table(show_header=True, header_style="bold bright_magenta", box=None, padding=(0, 2))
    table.add_column("Account", style="bold bright_cyan")
    table.add_column("Status", justify="center")
    table.add_column("Usage")
    table.add_column("Next Reset", justify="right", style="dim")

    for status in statuses:
        if status.email == active_email:
            status_text = "[bold bright_green]ACTIVE[/]"
        elif status.status == "ready":
            status_text = "[bold bright_green]READY[/]"
        else:
            status_text = "[bold bright_yellow]COOLDOWN[/]"

        usage = "\\n".join(format_model_usage(model) for model in status.models) or "unknown"
        next_available = format_remaining(status.remaining_seconds)
        table.add_row(
            status.email,
            status_text,
            usage,
            next_available,
        )
    console.print(
        Panel(
            table,
            title="[bold bright_cyan]Antigravity Cooldown[/]",
            border_style="bright_cyan",
            expand=False,
        )
    )
'''
content = re.sub(r'def print_statuses_table\(.*?\n\).*?expand=False,\n        \)\n    \)', new_impl.strip(), content, flags=re.DOTALL)
with open('src/antigravity_manager/cooldown.py', 'w') as f:
    f.write(content)

# Refactor doctor.py
with open('src/antigravity_manager/doctor.py', 'r') as f:
    content = f.read()

new_impl = '''
def print_doctor_table(checks: list[tuple[str, bool, str]]) -> None:
    from .banner import print_logo
    from .ui import Panel, Table, console

    print_logo()
    console.print("[bold cyan]🩺  Running System Diagnostic...[/]")

    table = Table(show_header=True, header_style="bold bright_magenta", box=None, padding=(0, 2))
    table.add_column("Component", style="bold bright_cyan")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="dim")

    all_ok = True
    for name, ok, detail in checks:
        if not ok:
            all_ok = False
        status_tag = "[success]OK[/]" if ok else "[danger]FAIL[/]"
        table.add_row(name, status_tag, detail)

    panel_style = "success" if all_ok else "danger"
    title_text = "[success]Diagnostic Passed[/]" if all_ok else "[danger]Diagnostic Failed[/]"

    console.print(
        Panel(
            table,
            title=title_text,
            border_style=panel_style,
            expand=False
        )
    )
'''
content = re.sub(r'def print_doctor_table\(.*?\n\).*?Diagnostic Complete\.\[/\]"\)', new_impl.strip(), content, flags=re.DOTALL)
with open('src/antigravity_manager/doctor.py', 'w') as f:
    f.write(content)
