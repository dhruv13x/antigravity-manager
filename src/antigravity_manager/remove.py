from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Group
from rich.text import Text

from .registry import load_registry, save_registry
from .ui import Confirm, Panel, console, render_dict_as_table


def perform_remove(args: Any) -> dict[str, Any]:
    email = args.email
    backup_dir = Path(args.backup_dir).expanduser()
    dry_run = getattr(args, "dry_run", False)
    force = getattr(args, "yes", False)

    results: dict[str, Any] = {
        "local_files_removed": [],
        "local_registry_removed": False,
        "cloud_files_removed": [],
        "cloud_registry_removed": False,
    }

    # 1. Identify local files
    local_files = []
    if backup_dir.exists():
        for p in backup_dir.glob("*"):
            is_match = f"-{email}-" in p.name or p.name.startswith(f"{email}-latest-")
            if is_match and (p.name.endswith(".tar.gz") or p.name.endswith(".metadata.json")):
                local_files.append(p)

    # 3. Confirmation
    if not force and not dry_run:
        console.print(
            f"\n[bold red]WARNING:[/] This will delete all backups and registry entries for [cyan]{email}[/]."
        )
        console.print(f"Local files to remove: [bold]{len(local_files)}[/]")
        if not Confirm.ask(
            f"[bold yellow]Are you sure you want to remove all traces of {email}?[/]"
        ):
            console.print("[blue]Removal cancelled.[/]")
            return results

    # 4. Execute Local Removal
    for p in local_files:
        if not dry_run:
            p.unlink()
        results["local_files_removed"].append(str(p))

    registry = load_registry()
    if email in registry:
        if not dry_run:
            del registry[email]
            save_registry(registry)
        results["local_registry_removed"] = True

    return results


def remove_result_to_text(results: dict[str, Any], email: str, dry_run: bool) -> Panel:
    title = (
        "[bold yellow]Dry Run: Remove Plan[/]"
        if dry_run
        else "[bold bright_green]Remove Completed[/]"
    )

    data = {
        "Email": email,
        "Local Files Removed": str(len(results.get("local_files_removed", []))),
        "Local Registry Removed": "[bold bright_green]YES[/]"
        if results.get("local_registry_removed")
        else "[dim]NO (not found)[/]",
    }

    table = render_dict_as_table(data)
    renderables = [table]

    if results.get("local_files_removed"):
        details = Text("\nFiles Removed:\n", style="bold cyan")
        for file in results["local_files_removed"]:
            details.append(f"  - {file}\n", style="dim")
        renderables.append(details)

    return Panel(
        Group(*renderables),
        title=title,
        border_style="yellow" if dry_run else "bright_green",
        expand=False,
    )
