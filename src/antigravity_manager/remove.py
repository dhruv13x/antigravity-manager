from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import SAFETY_BACKUP_DIR
from .registry import load_registry, save_registry
from .ui import Confirm, RenderableType, console


def perform_remove(args: Any) -> dict[str, Any]:
    email = args.email
    backup_dir = Path(args.backup_dir).expanduser()
    dry_run = getattr(args, "dry_run", False)
    force = getattr(args, "yes", False)

    results: dict[str, Any] = {
        "local_files_removed": [],
        "safety_backups_removed": [],
        "local_registry_removed": False,
        "cloud_files_removed": [],
        "cloud_registry_removed": False,
    }

    # 1. Identify local files (backups and metadata)
    local_files = []
    if backup_dir.exists():
        # Match pattern: email-latest- or -email-
        # We use re.escape to handle emails with dots/plus signs safely
        import re
        safe_email = re.escape(email)
        # Pattern for standard backups: {email}-latest or ...-{email}-...
        backup_pattern = re.compile(rf"(^|[-]){safe_email}(-|latest-)")
        
        for p in backup_dir.rglob("*"):
            if not p.is_file() and not p.is_symlink():
                continue
            
            if backup_pattern.search(p.name):
                # Ensure it's a known extension to avoid matching random junk
                if p.name.endswith((".tar.gz", ".tar.gz.gpg", ".metadata.json")):
                    local_files.append(p)
                    continue

            # Check status directory specific matches
            if "status" in p.parts and (f"email_{email}" in p.name or p.name == f"{email}.status.json"):
                local_files.append(p)

    # 2. Identify safety backups
    safety_files = []
    if SAFETY_BACKUP_DIR.exists():
        import re
        safe_email = re.escape(email)
        # Safety backups use: timestamp-{email}-pre-purge or timestamp-{email}-auto
        safety_pattern = re.compile(rf"-{safe_email}-(pre-purge|auto|latest)")
        
        for p in SAFETY_BACKUP_DIR.glob("*"):
            if safety_pattern.search(p.name):
                safety_files.append(p)

    # 3. Confirmation
    if not force and not dry_run:
        console.print(
            f"\n[bold red]WARNING:[/] This will delete all backups and registry entries for [cyan]{email}[/]."
        )
        console.print(f"Local files to remove: [bold]{len(local_files)}[/]")
        console.print(f"Safety backups to remove: [bold]{len(safety_files)}[/]")
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

    for p in safety_files:
        if not dry_run:
            if p.is_dir():
                import shutil

                shutil.rmtree(p)
            else:
                p.unlink()
        results["safety_backups_removed"].append(str(p))

    registry = load_registry()
    if email in registry:
        if not dry_run:
            del registry[email]
            save_registry(registry)
        results["local_registry_removed"] = True

    return results


def remove_result_to_text(results: dict[str, Any], email: str, dry_run: bool) -> RenderableType:
    from .ui import Panel, Tree

    title = (
        f"[warning]Remove Plan for {email} (Dry Run)[/]"
        if dry_run
        else f"[danger]Account Removed: {email}[/]"
    )
    border_style = "warning" if dry_run else "danger"

    tree = Tree(f"[bold red]Traces Removed for {email}[/]")

    if results.get("local_files_removed"):
        for path in results["local_files_removed"]:
            tree.add(f"[bold]local file[/]: {path}")

    if results.get("local_registry_removed"):
        tree.add(f"[bold]registry entry[/]: {email}")

    if results.get("safety_backups_removed"):
        for path in results["safety_backups_removed"]:
            tree.add(f"[bold]safety backup[/]: {path}")

    if results.get("cloud_files_removed"):
        for path in results["cloud_files_removed"]:
            tree.add(f"[bold]cloud file[/]: {path}")

    if (
        not results.get("local_files_removed")
        and not results.get("local_registry_removed")
        and not results.get("safety_backups_removed")
        and not results.get("cloud_files_removed")
    ):
        tree.add(f"[yellow]No removal actions taken for {email}.[/]")

    return Panel(tree, title=title, border_style=border_style, expand=False)
