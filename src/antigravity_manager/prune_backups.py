from __future__ import annotations

from pathlib import Path

from .list_backups import build_backup_entry, iter_backup_archives
from .ui import console, print_info, print_warning, print_error, print_success


def perform_prune_backups(
    backup_dir: Path,
    keep: int | None = None,
    keep_latest_per_email: bool = False,
    dry_run: bool = False,
) -> None:
    if keep is None and not keep_latest_per_email:
        print_info("Nothing to do: must specify --keep or --keep-latest-per-email")
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
            print_error(
                "--keep 0 is not executable. One copy per email backup "
                "will always stay until manually deleted by the user."
            )
            return

        email_counts: dict[str, int] = {}
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
        print_info("No backups matched pruning criteria.")
        return

    for entry in to_delete:
        if dry_run:
            print_info(f"\\[DRY RUN] Would delete [cyan]{entry.archive_path.name}[/]")
            metadata_path = entry.archive_path.with_name(
                entry.archive_path.name.replace(".tar.gz", ".metadata.json")
            )
            if metadata_path.exists():
                print_info(f"\\[DRY RUN] Would delete [cyan]{metadata_path.name}[/]")
            continue

        print_info(f"Deleting [cyan]{entry.archive_path.name}[/]...")
        try:
            entry.archive_path.unlink()
            metadata_path = entry.archive_path.with_name(
                entry.archive_path.name.replace(".tar.gz", ".metadata.json")
            )
            if metadata_path.exists():
                print_info(f"Deleting [cyan]{metadata_path.name}[/]...")
                metadata_path.unlink()
            print_success(f"Successfully deleted {entry.archive_path.name}")
        except OSError as e:
            print_error(f"Error deleting file: {e}")
