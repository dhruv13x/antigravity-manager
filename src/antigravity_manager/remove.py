from __future__ import annotations

from pathlib import Path
from typing import Any

from .registry import load_registry, save_registry
from .ui import Confirm, console


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
            if f"-{email}-" in p.name and (
                p.name.endswith(".tar.gz") or p.name.endswith(".metadata.json")
            ):
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


def remove_result_to_text(results: dict[str, Any], email: str, dry_run: bool) -> str:
    lines = [
        f"mode: {'dry-run' if dry_run else 'removed'}",
        f"email: {email}",
    ]

    lines.append(f"local_files_removed: {len(results['local_files_removed'])}")
    for f in results["local_files_removed"]:
        lines.append(f"  - {f}")

    lines.append(
        f"local_registry_removed: {'YES' if results['local_registry_removed'] else 'NO (not found)'}"
    )

    return "\n".join(lines)
