from __future__ import annotations

from pathlib import Path
from typing import Any

from .registry import load_registry, save_registry
from .ui import Confirm, console, print_info, print_warning, print_error, print_success, print_panel, Table


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
            if is_match and (
                p.name.endswith(".tar.gz") or p.name.endswith(".metadata.json")
            ):
                local_files.append(p)

    # 3. Confirmation
    if not force and not dry_run:
        print_warning(f"This will delete all backups and registry entries for [cyan]{email}[/].")
        print_info(f"Local files to remove: [bold]{len(local_files)}[/]")
        if not Confirm.ask(f"[warning]Are you sure you want to remove all traces of {email}?[/]"):
            print_info("Removal cancelled.")
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


def remove_result_to_text(results: dict[str, Any], email: str, dry_run: bool) -> str:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="info")
    table.add_column("Value", style="muted")

    table.add_row("Mode", "[warning]DRY RUN[/]" if dry_run else "[success]REMOVED[/]")
    table.add_row("Email", email)
    table.add_row("Local Files Removed", str(len(results["local_files_removed"])))
    table.add_row("Local Registry Removed", "[success]YES[/]" if results["local_registry_removed"] else "[warning]NO (not found)[/]")

    print_panel(table, title="Removal Result", style="success")

    if results["local_files_removed"]:
        print_info("Files removed:")
        for f in results["local_files_removed"]:
            print_info(f"  - {f}")

    return ""
