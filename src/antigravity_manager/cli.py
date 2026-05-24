from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .backup import backup_result_to_text, perform_backup
from .config import (
    ANTIGRAVITY_HOME,
    DEFAULT_BACKUP_DIR,
    DEFAULT_COOLDOWN_DISPLAY_LIMIT,
    DEFAULT_DECISION_MODEL,
    GEMINI_HOME,
)
from .cooldown import evaluate_entries, format_remaining, print_statuses_table
from .doctor import print_doctor_table, run_doctor
from .list_backups import list_backups, print_entries_table
from .prune import perform_prune, prune_result_to_text
from .prune_backups import perform_prune_backups
from .registry import update_registry_from_status
from .restore import perform_restore, restore_result_to_text
from .status import (
    capture_tmux_status_text,
    live_status_to_text,
    parse_live_status_text,
    status_to_dict,
)
from .ui import console
from .purge import perform_purge
from .remove import perform_remove
from .profile import perform_profile
from .sync import perform_sync


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agm", description="Manage Antigravity CLI accounts, backups, and cooldowns."
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "-s", "--status", action="store_true", help="Shortcut for 'status' command."
    )
    parser.add_argument(
        "-c", "--cooldown", action="store_true", help="Shortcut for 'cooldown' command (default)."
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    status_parser = subparsers.add_parser(
        "status", help="Capture and parse live Antigravity /usage status."
    )
    status_parser.add_argument("--input-file", help="Read captured status text from a file.")
    status_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    add_tmux_args(status_parser)

    backup_parser = subparsers.add_parser("backup", help="Create an Antigravity backup archive.")
    backup_parser.add_argument(
        "--source-dir", default=str(ANTIGRAVITY_HOME), help="Antigravity CLI directory."
    )
    backup_parser.add_argument(
        "--gemini-home",
        default=str(GEMINI_HOME),
        help="Gemini home containing shared identity files.",
    )
    backup_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup output directory."
    )
    backup_parser.add_argument(
        "--status-file", help="Read captured status text from a file instead of live capture."
    )
    backup_parser.add_argument(
        "--without-status-check",
        action="store_true",
        help="Skip live status and use fallback metadata.",
    )
    backup_parser.add_argument(
        "--auth-only", action="store_true", help="Archive only identity/auth files."
    )
    backup_parser.add_argument(
        "--include-bin", action="store_true", help="Include bundled Antigravity binaries."
    )
    backup_parser.add_argument(
        "--include-logs", action="store_true", help="Include Antigravity logs."
    )
    backup_parser.add_argument(
        "--decision-model",
        default=DEFAULT_DECISION_MODEL,
        help="Model used for backup naming and recommendations.",
    )
    backup_parser.add_argument("--dry-run", action="store_true", help="Show what would be created.")
    backup_parser.add_argument("--force", action="store_true", help="Overwrite existing archive.")
    add_tmux_args(backup_parser)

    restore_parser = subparsers.add_parser("restore", help="Restore an Antigravity backup.")
    restore_parser.add_argument("--from-archive", help="Specific backup archive to restore.")
    restore_parser.add_argument("--email", help="Restore latest backup for this email.")
    restore_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup directory."
    )
    restore_parser.add_argument(
        "--dest-dir",
        default=str(ANTIGRAVITY_HOME),
        help="Antigravity CLI directory to restore into.",
    )
    restore_parser.add_argument(
        "--gemini-home",
        default=str(GEMINI_HOME),
        help="Gemini home containing shared identity files.",
    )
    restore_parser.add_argument(
        "--full",
        action="store_true",
        help="Restore full Antigravity state instead of auth-only files.",
    )
    restore_parser.add_argument(
        "--force",
        action="store_true",
        help="For full restore, delete destination instead of moving it to safety backup.",
    )
    restore_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be restored."
    )

    cooldown_parser = subparsers.add_parser(
        "cooldown", help="Show account/model availability from status registry and backups."
    )
    cooldown_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup directory."
    )
    cooldown_parser.add_argument(
        "--limit", type=int, default=DEFAULT_COOLDOWN_DISPLAY_LIMIT, help="Maximum rows to display."
    )
    cooldown_parser.add_argument(
        "--decision-model",
        default=DEFAULT_DECISION_MODEL,
        help="Model used to decide READY/COOLDOWN.",
    )
    cooldown_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    list_parser = subparsers.add_parser("list-backups", help="List Antigravity backups.")
    list_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup directory."
    )
    list_parser.add_argument("--email", help="Filter by email.")
    list_parser.add_argument(
        "--latest-per-email", action="store_true", help="Show only latest backup per account."
    )
    list_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    recommend_parser = subparsers.add_parser(
        "recommend", help="Recommend the best account to use next."
    )
    recommend_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup directory."
    )
    recommend_parser.add_argument(
        "--decision-model",
        default=DEFAULT_DECISION_MODEL,
        help="Model used to pick the recommendation.",
    )
    recommend_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    recommend_parser.add_argument(
        "--use", action="store_true", help="Immediately auth-only restore the recommended account."
    )
    recommend_parser.add_argument(
        "--dest-dir",
        default=str(ANTIGRAVITY_HOME),
        help="Antigravity CLI directory to restore into.",
    )
    recommend_parser.add_argument(
        "--gemini-home",
        default=str(GEMINI_HOME),
        help="Gemini home containing shared identity files.",
    )
    recommend_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be restored with --use."
    )

    use_parser = subparsers.add_parser("use", help="Auth-only restore for an account.")
    use_parser.add_argument("email", help="Account email to switch to.")
    use_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup directory."
    )
    use_parser.add_argument(
        "--dest-dir",
        default=str(ANTIGRAVITY_HOME),
        help="Antigravity CLI directory to restore into.",
    )
    use_parser.add_argument(
        "--gemini-home",
        default=str(GEMINI_HOME),
        help="Gemini home containing shared identity files.",
    )
    use_parser.add_argument("--dry-run", action="store_true", help="Show what would be restored.")

    doctor_parser = subparsers.add_parser(
        "doctor", help="Check local Antigravity Manager prerequisites."
    )
    doctor_parser.add_argument(
        "--source-dir", default=str(ANTIGRAVITY_HOME), help="Antigravity CLI directory."
    )
    doctor_parser.add_argument(
        "--gemini-home",
        default=str(GEMINI_HOME),
        help="Gemini home containing shared identity files.",
    )
    doctor_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup directory."
    )
    doctor_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    prune_parser = subparsers.add_parser("prune", help="Prune temporary runtime state.")
    prune_parser.add_argument("--source-dir", default=str(ANTIGRAVITY_HOME), help="Antigravity CLI directory.")
    prune_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without deleting.")

    prune_backups_parser = subparsers.add_parser("prune-backups", help="Delete old backup archives and metadata.")
    prune_backups_parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup directory.")
    prune_backups_parser.add_argument("--keep", type=int, help="Number of backups to keep per email.")
    prune_backups_parser.add_argument("--keep-latest-per-email", action="store_true", help="Keep only the latest backup per email.")
    prune_backups_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without deleting.")

    purge_parser = subparsers.add_parser("purge", help="Purge caches.")
    purge_parser.add_argument("--source-dir", default=str(ANTIGRAVITY_HOME), help="Antigravity CLI directory.")
    purge_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed.")
    purge_parser = subparsers.add_parser("purge", help="Purge caches.")
    purge_parser.add_argument("--source-dir", default=str(ANTIGRAVITY_HOME), help="Antigravity CLI directory.")
    purge_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed.")
    purge_parser = subparsers.add_parser("purge", help="Purge caches.")
    purge_parser.add_argument("--source-dir", default=str(ANTIGRAVITY_HOME), help="Antigravity CLI directory.")
    purge_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed.")
    purge_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation.")
    purge_parser.set_defaults(command="purge")

    remove_parser = subparsers.add_parser("remove", help="Remove data.")
    remove_parser.set_defaults(command="remove")

    profile_parser = subparsers.add_parser("profile", help="Manage profiles.")
    profile_parser.set_defaults(command="profile")

    sync_parser = subparsers.add_parser("sync", help="Sync backups.")
    sync_parser.set_defaults(command="sync")

    return parser


def add_tmux_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agy-command", default="agy", help="Command used to launch Antigravity.")
    parser.add_argument("--tmux-session-name", default=None, help="Temporary tmux session name.")
    parser.add_argument("--tmux-cols", type=int, default=140, help="tmux capture width.")
    parser.add_argument("--tmux-rows", type=int, default=45, help="tmux capture height.")
    parser.add_argument(
        "--startup-timeout-seconds", type=float, default=30.0, help="Startup wait timeout."
    )
    parser.add_argument(
        "--usage-timeout-seconds", type=float, default=30.0, help="/usage wait timeout."
    )


def handle_status(args: argparse.Namespace) -> None:
    if args.input_file:
        text = Path(args.input_file).expanduser().read_text(encoding="utf-8")
    else:
        text = capture_tmux_status_text(
            session_name=args.tmux_session_name,
            agy_command=args.agy_command,
            cols=args.tmux_cols,
            rows=args.tmux_rows,
            startup_timeout_seconds=args.startup_timeout_seconds,
            usage_timeout_seconds=args.usage_timeout_seconds,
        )
    status = parse_live_status_text(text)
    update_registry_from_status(status)
    if args.json:
        console.print(json.dumps(status_to_dict(status), indent=2), markup=False)
    else:
        console.print(live_status_to_text(status))


def handle_backup(args: argparse.Namespace) -> None:
    archive_path, metadata_path, metadata = perform_backup(args)
    console.print(
        backup_result_to_text(archive_path, metadata_path, metadata, dry_run=args.dry_run)
    )


def handle_restore(args: argparse.Namespace) -> None:
    archive_path, metadata, restored_files, safety_path = perform_restore(args)
    console.print(
        restore_result_to_text(
            archive_path,
            metadata,
            restored_files,
            safety_path,
            dry_run=args.dry_run,
            full=args.full,
        )
    )


def handle_cooldown(args: argparse.Namespace) -> None:
    entries = list_backups(Path(args.backup_dir).expanduser(), latest_per_email=True)
    statuses = evaluate_entries(entries, decision_model=args.decision_model)[: args.limit]
    if args.json:
        console.print(
            json.dumps([asdict(item) for item in statuses], indent=2, default=str), markup=False
        )
    else:
        print_statuses_table(statuses)


def handle_list_backups(args: argparse.Namespace) -> None:
    entries = list_backups(
        Path(args.backup_dir).expanduser(),
        email=args.email,
        latest_per_email=args.latest_per_email,
    )
    if args.json:
        console.print(
            json.dumps([asdict(item) for item in entries], indent=2, default=str), markup=False
        )
    else:
        print_entries_table(entries)


def handle_recommend(args: argparse.Namespace) -> None:
    entries = list_backups(Path(args.backup_dir).expanduser(), latest_per_email=True)
    statuses = evaluate_entries(entries, decision_model=args.decision_model)
    if not statuses:
        raise FileNotFoundError("No account status or backup metadata found.")
    selected = statuses[0]
    if args.json:
        console.print(json.dumps(asdict(selected), indent=2, default=str), markup=False)
    else:
        console.print(
            "\n".join(
                [
                    f"email: {selected.email}",
                    f"status: {selected.status}",
                    f"decision_model: {selected.decision_model}",
                    (
                        "decision_model_available: "
                        f"{selected.decision_model_status.is_available if selected.decision_model_status else 'unknown'}"
                    ),
                    ("available_in: " f"{format_remaining(selected.remaining_seconds)}"),
                    f"all_models: {selected.available_models}/{selected.total_models}",
                    f"source: {selected.source}",
                ]
            )
        )
    if args.use:
        args.email = selected.email
        args.full = False
        args.force = False
        args.from_archive = None
        handle_use(args)


def handle_use(args: argparse.Namespace) -> None:
    args.full = False
    args.force = False
    args.from_archive = None
    archive_path, metadata, restored_files, safety_path = perform_restore(args)
    console.print(
        restore_result_to_text(
            archive_path,
            metadata,
            restored_files,
            safety_path,
            dry_run=args.dry_run,
            full=False,
        )
    )


def handle_doctor(args: argparse.Namespace) -> None:
    checks = run_doctor(
        antigravity_home=Path(args.source_dir).expanduser(),
        gemini_home=Path(args.gemini_home).expanduser(),
        backup_dir=Path(args.backup_dir).expanduser(),
    )
    if args.json:
        console.print(
            json.dumps(
                [{"name": name, "ok": ok, "detail": detail} for name, ok, detail in checks],
                indent=2,
            ),
            markup=False,
        )
    else:
        print_doctor_table(checks)


def handle_prune(args: argparse.Namespace) -> None:
    plan = perform_prune(args)
    console.print(prune_result_to_text(plan, dry_run=args.dry_run, source_dir=Path(args.source_dir)))


def handle_prune_backups(args: argparse.Namespace) -> None:
    perform_prune_backups(
        backup_dir=Path(args.backup_dir).expanduser(),
        keep=args.keep,
        keep_latest_per_email=args.keep_latest_per_email,
        dry_run=args.dry_run,
    )

def handle_purge(args: argparse.Namespace) -> None:
    perform_purge(args)

def handle_remove(args: argparse.Namespace) -> None:
    perform_remove(args)

def handle_profile(args: argparse.Namespace) -> None:
    perform_profile(args)

def handle_sync(args: argparse.Namespace) -> None:
    perform_sync(args)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Handle shortcuts and default command
    if args.status:
        args.command = "status"
        # Populate defaults for status if not provided via subcommand
        if not hasattr(args, "input_file"):
            args.input_file = None
            args.json = False
            args.agy_command = "agy"
            args.tmux_session_name = None
            args.tmux_cols = 140
            args.tmux_rows = 45
            args.startup_timeout_seconds = 30.0
            args.usage_timeout_seconds = 30.0
    elif args.cooldown or args.command is None:
        args.command = "cooldown"
        # Populate defaults for cooldown if not provided via subcommand
        if not hasattr(args, "backup_dir"):
            args.backup_dir = str(DEFAULT_BACKUP_DIR)
            args.limit = DEFAULT_COOLDOWN_DISPLAY_LIMIT
            args.decision_model = DEFAULT_DECISION_MODEL
            args.json = False

    handlers = {
        "status": handle_status,
        "backup": handle_backup,
        "restore": handle_restore,
        "cooldown": handle_cooldown,
        "list-backups": handle_list_backups,
        "recommend": handle_recommend,
        "use": handle_use,
        "doctor": handle_doctor,
        "prune": handle_prune,
        "prune-backups": handle_prune_backups,
        "purge": handle_purge,
        "remove": handle_remove,
        "profile": handle_profile,
        "sync": handle_sync,
    }
    try:
        handlers[args.command](args)
    except (FileNotFoundError, FileExistsError, ValueError, RuntimeError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
