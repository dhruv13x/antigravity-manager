from __future__ import annotations

from pathlib import Path

from .list_backups import build_backup_entry, iter_backup_archives
from .ui import console

def perform_prune_backups(
    backup_dir: Path,
    keep: int | None = None,
    keep_latest_per_email: bool = False,
    dry_run: bool = False,
) -> None:
    if keep is None and not keep_latest_per_email:
        console.print("Nothing to do: must specify --keep or --keep-latest-per-email")
        return

    raw_entries = [build_backup_entry(path) for path in iter_backup_archives(backup_dir)]
    entries = [e for e in raw_entries if e is not None]

    # Sort chronologically, newest first
    entries.sort(key=lambda e: e.created_at, reverse=True)

    to_delete = []

    if keep_latest_per_email:
        seen_emails = set()
        kept = []
        for e in entries:
            if e.email not in seen_emails:
                seen_emails.add(e.email)
                kept.append(e)
            else:
                to_delete.append(e)
        entries = kept

    if keep is not None:
        if keep < 1:
            console.print(
                "[bold red]Error:[/] --keep 0 is not executable. One copy per email backup "
                "will always stay until manually deleted by the user."
            )
            return

        email_counts = {}
        kept = []
        for e in entries:
            count = email_counts.get(e.email, 0)
            if count < keep:
                email_counts[e.email] = count + 1
                kept.append(e)
            else:
                to_delete.append(e)
        entries = kept

    if not to_delete:
        console.print("No backups matched pruning criteria.")
        return

    for entry in to_delete:
        if dry_run:
            console.print(f"Would delete {entry.archive_path.name}")
            metadata_path = entry.archive_path.with_name(
                entry.archive_path.name.replace(".tar.gz", ".metadata.json")
            )
            if metadata_path.exists():
                console.print(f"Would delete {metadata_path.name}")
            continue

        console.print(f"Deleting {entry.archive_path.name}...")
        try:
            entry.archive_path.unlink()
            metadata_path = entry.archive_path.with_name(
                entry.archive_path.name.replace(".tar.gz", ".metadata.json")
            )
            if metadata_path.exists():
                console.print(f"Deleting {metadata_path.name}...")
                metadata_path.unlink()
        except OSError as e:
            console.print(f"Error deleting file: {e}")