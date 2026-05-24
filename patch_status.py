import re

with open('src/antigravity_manager/status.py', 'r') as f:
    content = f.read()

# Replace live_status_to_text implementation
new_impl = '''
def live_status_to_text(status: LiveStatus) -> "Panel":
    from .ui import Panel, Table, Group, Text

    header = Table.grid(padding=(0, 2))
    header.add_column(style="bold cyan", justify="right")
    header.add_column(style="white")

    header.add_row("Account:", status.email)
    header.add_row("Plan:", f"{status.plan} [dim]({'PRO' if status.is_pro else 'STANDARD'})[/dim]")
    header.add_row("Captured At:", status.captured_at.strftime("%Y-%m-%d %H:%M:%S %Z"))

    model_table = Table(show_header=True, header_style="bold bright_magenta", box=None)
    model_table.add_column("Model", style="bold bright_cyan")
    model_table.add_column("Quota", justify="right")
    model_table.add_column("State", justify="center")
    model_table.add_column("Refresh", justify="right", style="dim")

    for model in status.models:
        quota_text = f"{model.quota_percent_left}%" if model.quota_percent_left is not None else "unknown"

        if model.is_available:
            state_text = "[success]Ready[/]"
        else:
            state_text = "[danger]Cooldown[/]"

        if model.quota_percent_left is not None:
            if model.quota_percent_left >= 50:
                quota_text = f"[success]{quota_text}[/]"
            elif model.quota_percent_left >= 20:
                quota_text = f"[warning]{quota_text}[/]"
            elif model.quota_percent_left > 0:
                quota_text = f"[yellow]{quota_text}[/]"
            else:
                quota_text = f"[danger]{quota_text}[/]"

        refresh_text = model.refresh_in_text or "available now"

        model_table.add_row(
            model.model_name,
            quota_text,
            state_text,
            refresh_text
        )

    content_group = Group(
        header,
        Text(""),
        Text("Models:", style="bold bright_magenta"),
        model_table
    )

    return Panel(
        content_group,
        title="[bold bright_cyan]Antigravity Live Status[/]",
        border_style="bright_cyan",
        expand=False,
    )
'''

content = re.sub(r'def live_status_to_text\(status: LiveStatus\) -> str:.*?(?=\Z|\n\n\w)', new_impl.strip(), content, flags=re.DOTALL)

with open('src/antigravity_manager/status.py', 'w') as f:
    f.write(content)
