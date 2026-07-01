from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from . import __version__
from .backup import (
    backup_result_to_text,
    perform_backup,
    read_token_fingerprint_from_archive,
    read_token_fingerprint_from_path,
)
from .config import (
    ACTIVE_ACCOUNT_PATH,
    ANTIGRAVITY_HOME,
    ANTIGRAVITY_SESSION_DIR,
    DEFAULT_BACKUP_DIR,
    DEFAULT_COOLDOWN_DISPLAY_LIMIT,
    DEFAULT_DECISION_MODEL,
    GEMINI_CONFIG_DIR,
)
from .cooldown import evaluate_entries, format_remaining, print_statuses_table
from .credentials import resolve_credentials
from .doctor import print_doctor_table, run_doctor
from .list_backups import list_backups, list_status_metadata, print_entries_table
from .profile import export_profile, import_profile
from .prune import perform_prune, prune_result_to_text

from .purge import perform_purge, purge_result_to_text
from .registry import update_registry_from_status
from .remove import perform_remove, remove_result_to_text
from .restore import perform_restore, resolve_archive_path, restore_result_to_text
from .status import (
    AntigravityStatusError,
    LiveStatus,
    capture_tmux_status_text,
    live_status_to_text,
    parse_live_status_text,
    status_to_dict,
)
from .sync import (
    delete_cloud_account_objects,
    delete_cloud_objects,
    pull_backup,
    pull_cloud_index,
    push_backup,
    sync_auto,
)
from .ui import banner, console, error_console, print_rich_help
from .utils import build_archive_name, safe_label, read_active_email


def save_status_metadata(status: LiveStatus, backup_dir: Path) -> Path:
    next_available_at = status_metadata_timestamp(status)
    latest_path = backup_dir / f"{safe_label(status.email)}-latest-antigravity.metadata.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    
    metadata = {}
    if latest_path.exists():
        try:
            metadata = json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    metadata.update({
        "schema_version": 1,
        "product": "antigravity",
        "email": status.email,
        "plan": status.plan,
        "captured_at": status.captured_at.isoformat(),
        "next_available_at": next_available_at.isoformat(),
        "status": status_to_dict(status),
    })
    metadata.setdefault("created_at", status.captured_at.isoformat())
    metadata.setdefault("record_type", "status")
    metadata.setdefault("archive_name", None)
    metadata.setdefault("archive_path", None)
    metadata.setdefault("backup_mode", "status-only")

    if metadata.get("archive_name") is not None:
        metadata.pop("record_type", None)

    metadata_text = json.dumps(metadata, indent=2, sort_keys=True)
    latest_path.write_text(metadata_text, encoding="utf-8")
    return latest_path





def status_state(status: LiveStatus) -> str:
    if any(model.block_reason for model in status.models):
        return "blocked"
    if any(model.is_available for model in status.models):
        return "ready"
    return "cooldown"


def status_metadata_timestamp(status: LiveStatus) -> datetime:
    # Try to find the refresh time of the primary decision model
    # We look for "Gemini" and "Flash" as a fallback for the new grouping
    for model in status.models:
        model_name = model.model_name.lower()
        # Old format: "Gemini 3.5 Flash (High)"
        # New format: "GEMINI MODELS (Gemini Flash, Gemini Pro)"
        if "gemini" in model_name and "flash" in model_name:
            if model.refresh_at is not None:
                return model.refresh_at
            
    # Fallback to the furthest refresh time if we can't find Gemini Flash
    refreshes = [m.refresh_at for m in status.models if m.refresh_at is not None]
    if refreshes:
        return max(refreshes)
        
    return status.captured_at


def save_active_account(email: str, *, dry_run: bool = False) -> None:
    if dry_run:
        return
    ACTIVE_ACCOUNT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_ACCOUNT_PATH.write_text(
        json.dumps(
            {"schema_version": 1, "email": email, "updated_at": datetime.now().astimezone().isoformat()},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def add_status_skip_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-status",
        action="store_true",
        dest="no_status",
        help="Skip live status capture.",
    )


def add_cloud_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cloud", action="store_true", help="Read required metadata from cloud first.")
    parser.add_argument("--bucket-name", help="B2/S3 bucket name.")
    parser.add_argument("--endpoint-url", help="S3 endpoint URL.")
    parser.add_argument("--access-key", help="S3 access key.")
    parser.add_argument("--secret-key", help="S3 secret key.")


def pull_cloud_index_if_requested(
    args: argparse.Namespace, *, override_backup_dir: Path | None = None
) -> None:
    if not getattr(args, "cloud", False):
        return
    access_key, secret_key, bucket_name, endpoint_url = resolve_credentials(args)
    pull_cloud_index(
        backup_dir=override_backup_dir or Path(args.backup_dir).expanduser(),
        bucket_name=bucket_name,
        endpoint_url=endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        dry_run=getattr(args, "dry_run", False),
    )


def pull_cloud_backup_if_requested(
    args: argparse.Namespace, *, override_backup_dir: Path | None = None
) -> None:
    if not getattr(args, "cloud", False):
        return
    access_key, secret_key, bucket_name, endpoint_url = resolve_credentials(args)
    pull_backup(
        backup_dir=override_backup_dir or Path(args.backup_dir).expanduser(),
        bucket_name=bucket_name,
        endpoint_url=endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        dry_run=getattr(args, "dry_run", False),
    )


def capture_and_save_current_status(args: argparse.Namespace) -> LiveStatus | None:
    if getattr(args, "dry_run", False) or getattr(args, "no_status", False):
        return None
    dest_dir_val = getattr(args, "dest_dir", None) or getattr(args, "source_dir", None) or ANTIGRAVITY_HOME
    token_path = Path(dest_dir_val).expanduser() / "antigravity-oauth-token"
    if not token_path.exists():
        return None
    try:
        text = capture_tmux_status_text(
            session_name=getattr(args, "tmux_session_name", None),
            agy_command=getattr(args, "agy_command", "agy"),
            cols=getattr(args, "tmux_cols", 140),
            rows=getattr(args, "tmux_rows", 45),
            startup_timeout_seconds=getattr(args, "startup_timeout_seconds", 30.0),
            usage_timeout_seconds=getattr(args, "usage_timeout_seconds", 30.0),
        )
        status = parse_live_status_text(text)
    except Exception as exc:
        raise AntigravityStatusError(
            "Current account status could not be captured. Switch aborted. "
            "Use --no-status only for first setup or corrupt current credentials."
        ) from exc
    update_registry_from_status(status)
    save_status_metadata(status, Path(args.backup_dir).expanduser())
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agm",
        description="Manage Antigravity CLI accounts, backups, and cooldowns.",
        add_help=False,
    )
    parser.add_argument(
        "-h", "--help", action="store_true", help="Show this help message and exit."
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
    status_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Metadata output directory."
    )
    status_parser.add_argument(
        "--no-save", action="store_true", help="Display status without updating saved metadata."
    )
    status_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    add_tmux_args(status_parser)

    backup_parser = subparsers.add_parser("backup", help="Create an Antigravity backup archive.")
    backup_parser.add_argument(
        "--source-dir", default=str(ANTIGRAVITY_HOME), help="Antigravity CLI directory."
    )
    backup_parser.add_argument(
        "--gemini-home",
        default=None,
        help=argparse.SUPPRESS,
    )
    backup_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup output directory."
    )
    backup_parser.add_argument(
        "--status-file", help="Read captured status text from a file instead of live capture."
    )
    add_status_skip_args(backup_parser)
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
    backup_parser.add_argument(
        "--encrypt", action="store_true", help="Encrypt the archive with GPG."
    )
    add_tmux_args(backup_parser)

    restore_parser = subparsers.add_parser("restore", help="Full restore an Antigravity backup.")
    restore_parser.add_argument(
        "target",
        nargs="?",
        help="Account email, archive filename, or archive path to restore.",
    )
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
        default=None,
        help=argparse.SUPPRESS,
    )
    restore_parser.add_argument(
        "--full",
        action="store_true",
        default=None,
        help="Restore full Antigravity state instead of auth-only files.",
    )
    restore_parser.add_argument(
        "--auth-only",
        action="store_true",
        help="Restore only account identity/auth files.",
    )
    restore_parser.add_argument(
        "--force",
        action="store_true",
        help="For full restore, delete destination instead of moving it to safety backup.",
    )
    restore_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be restored."
    )
    add_cloud_args(restore_parser)
    add_status_skip_args(restore_parser)
    add_tmux_args(restore_parser)

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
    add_cloud_args(cooldown_parser)

    list_parser = subparsers.add_parser("list-backups", help="List Antigravity backups.")
    list_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup directory."
    )
    list_parser.add_argument("--email", help="Filter by email.")
    list_parser.add_argument(
        "--all",
        action="store_true",
        help="Show all backups instead of only the latest backup per account.",
    )
    list_parser.add_argument(
        "--latest-per-email",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    list_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    add_cloud_args(list_parser)

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
        "--restore", action="store_true", help="Immediately full restore the recommended account."
    )
    recommend_parser.add_argument(
        "--dest-dir",
        default=str(ANTIGRAVITY_HOME),
        help="Antigravity CLI directory to restore into.",
    )
    recommend_parser.add_argument(
        "--gemini-home",
        default=None,
        help=argparse.SUPPRESS,
    )
    recommend_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be restored with --use."
    )
    add_cloud_args(recommend_parser)
    add_status_skip_args(recommend_parser)
    add_tmux_args(recommend_parser)

    use_parser = subparsers.add_parser("use", help="Auth-only restore for an account or archive.")
    use_parser.add_argument("target", help="Account email, archive filename, or archive path.")
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
        default=None,
        help=argparse.SUPPRESS,
    )
    use_parser.add_argument("--dry-run", action="store_true", help="Show what would be restored.")
    add_cloud_args(use_parser)
    add_status_skip_args(use_parser)
    add_tmux_args(use_parser)

    doctor_parser = subparsers.add_parser(
        "doctor", help="Check local Antigravity Manager prerequisites."
    )
    doctor_parser.add_argument(
        "--source-dir", default=str(ANTIGRAVITY_HOME), help="Antigravity CLI directory."
    )
    doctor_parser.add_argument(
        "--gemini-home",
        default=None,
        help=argparse.SUPPRESS,
    )
    doctor_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup directory."
    )
    doctor_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    prune_parser = subparsers.add_parser("prune", help="Prune temporary runtime state.")
    prune_parser.add_argument(
        "--source-dir", default=str(ANTIGRAVITY_HOME), help="Antigravity CLI directory."
    )
    prune_parser.add_argument(
        "--gemini-config-dir",
        default=str(GEMINI_CONFIG_DIR),
        help="Gemini project/session config directory.",
    )
    prune_parser.add_argument(
        "--session-dir",
        default=str(ANTIGRAVITY_SESSION_DIR),
        help="Antigravity session symlink/config directory.",
    )
    prune_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be removed without deleting."
    )



    purge_parser = subparsers.add_parser("purge", help="Completely reset Antigravity state.")
    purge_parser.add_argument(
        "--source-dir", default=str(ANTIGRAVITY_HOME), help="Antigravity CLI directory."
    )
    purge_parser.add_argument("-y", "--yes", action="store_true", help="Confirm deletion.")
    purge_parser.add_argument(
        "--gemini-config-dir",
        default=str(GEMINI_CONFIG_DIR),
        help="Gemini project/session config directory.",
    )
    purge_parser.add_argument(
        "--session-dir",
        default=str(ANTIGRAVITY_SESSION_DIR),
        help="Antigravity session symlink/config directory.",
    )
    purge_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be removed without deleting."
    )

    remove_parser = subparsers.add_parser("remove", aliases=["rm"], help="Remove all traces of a specific account.")
    remove_parser.add_argument("email", help="Account email to remove.")
    remove_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup directory."
    )
    remove_parser.add_argument(
        "-y", "--yes", action="store_true", help="Confirm removal without prompt."
    )
    remove_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be removed without deleting."
    )
    add_cloud_args(remove_parser)

    profile_parser = subparsers.add_parser("profile", help="Export or import manager profile.")
    profile_parser.add_argument("action", choices=["export", "import"], help="Action to perform.")
    profile_parser.add_argument("file", help="Profile archive path.")
    profile_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would happen without doing it."
    )

    sync_parser = subparsers.add_parser("sync", help="Sync backups with S3 bucket.")
    sync_parser.add_argument("direction", choices=["push", "pull", "auto"], help="Direction to sync.")
    sync_parser.add_argument(
        "--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Local backup directory."
    )
    sync_parser.add_argument("--bucket-name", help="S3 bucket name.")
    sync_parser.add_argument("--endpoint-url", help="S3 endpoint URL.")
    sync_parser.add_argument("--access-key", help="S3 access key.")
    sync_parser.add_argument("--secret-key", help="S3 secret key.")
    sync_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would sync without doing it."
    )

    return parser


def add_tmux_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agy-command", default="agy", help="Command used to launch Antigravity.")
    parser.add_argument("--tmux-session-name", default=None, help="Temporary tmux session name.")
    parser.add_argument("--tmux-cols", type=int, default=140, help="tmux capture width.")
    parser.add_argument("--tmux-rows", type=int, default=45, help="tmux capture height.")
    parser.add_argument(
        "--startup-timeout-seconds", type=float, default=15.0, help="Startup wait timeout."
    )
    parser.add_argument(
        "--usage-timeout-seconds", type=float, default=15.0, help="/usage wait timeout."
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
    
    # Try to load existing status for merging (handles partial probe scenarios)
    from .registry import load_registry
    from .status import ModelQuotaStatus
    from .list_backups import parse_dt
    
    existing_status = None
    try:
        # We don't know the email yet, so we have to parse it first then potentially re-parse
        # This is fast since it's just regex on local text
        email, _ = parse_email_and_plan(text)
        registry = load_registry()
        if email in registry:
            reg_entry = registry[email]
            status_data = reg_entry.get("status")
            if status_data:
                models = [
                    ModelQuotaStatus(
                        model_name=m.get("model_name", "unknown"),
                        quota_percent_left=m.get("quota_percent_left"),
                        refresh_in_text=m.get("refresh_in_text"),
                        refresh_at=parse_dt(m.get("refresh_at")) if m.get("refresh_at") else None,
                        is_available=m.get("is_available", False),
                        block_reason=m.get("block_reason"),
                    )
                    for m in status_data.get("models", [])
                ]
                existing_status = LiveStatus(
                    email=email,
                    plan=reg_entry.get("plan", "unknown"),
                    is_pro=reg_entry.get("is_pro", False),
                    captured_at=parse_dt(reg_entry.get("captured_at")) or datetime.now().astimezone(),
                    models=tuple(models)
                )
    except Exception:
        pass

    status = parse_live_status_text(text, existing_status=existing_status)
    if not getattr(args, "no_save", False):
        update_registry_from_status(status)
        save_status_metadata(status, Path(args.backup_dir).expanduser())
        save_active_account(status.email)
    if args.json:
        console.print(json.dumps(status_to_dict(status), indent=2), markup=False)
    else:
        console.print(live_status_to_text(status))


def handle_backup(args: argparse.Namespace) -> None:
    archive_path, metadata_path, metadata = perform_backup(args)
    console.print(
        backup_result_to_text(archive_path, metadata_path, metadata, dry_run=args.dry_run)
    )


def _auto_backup_before_switch(args: argparse.Namespace, status: LiveStatus | None) -> None:
    if not status or getattr(args, "dry_run", False):
        return

    try:
        console.print(
            f"[cyan]Auto-backing up active account ({status.email}) before restore...[/cyan]"
        )
        backup_args = argparse.Namespace(
            source_dir=getattr(args, "dest_dir", ANTIGRAVITY_HOME),
            backup_dir=args.backup_dir,
            no_status=True,
            status_file=None,
            auth_only=False,
            include_bin=False,
            include_logs=False,
            decision_model=getattr(args, "decision_model", DEFAULT_DECISION_MODEL),
            dry_run=False,
            force=True,
            encrypt=False,
        )
        archive_path, metadata_path, metadata = perform_backup(backup_args, status=status)
        console.print(
            backup_result_to_text(archive_path, metadata_path, metadata, dry_run=False)
        )
    except Exception as e:
        console.print(
            f"[warning]Failed to auto-backup active account before restore: {e}[/warning]"
        )


def _current_token_fingerprint(args: argparse.Namespace) -> str | None:
    state_dir = getattr(args, "dest_dir", None) or getattr(args, "source_dir", None) or ANTIGRAVITY_HOME
    return read_token_fingerprint_from_path(
        Path(state_dir).expanduser() / "antigravity-oauth-token"
    )


def _validate_restore_target(args: argparse.Namespace, archive_path: Path) -> None:
    if getattr(args, "dry_run", False):
        return

    current_fp = _current_token_fingerprint(args)
    archive_fp = read_token_fingerprint_from_archive(archive_path)
    if current_fp and archive_fp and current_fp == archive_fp:
        raise AntigravityStatusError(
            "Restore would have no effect. "
            f"The target archive already has the active OAuth credential "
            f"(token fingerprint: {archive_fp}). Choose a different account backup."
        )


def _validate_restored_account(args: argparse.Namespace, expected_email: str) -> LiveStatus | None:
    if getattr(args, "dry_run", False) or getattr(args, "no_status", False):
        return None

    status = capture_and_save_current_status(args)
    if status is None:
        return None

    if expected_email == "unknown" or status.email == expected_email:
        return status

    save_active_account(status.email, dry_run=getattr(args, "dry_run", False))

    raise AntigravityStatusError(
        "Restored account verification failed. "
        f"Backup metadata says '{expected_email}', but live Antigravity authenticated as "
        f"'{status.email}'. The archive credential does not belong to the labeled email."
    )


def handle_restore(args: argparse.Namespace) -> None:
    if getattr(args, "auth_only", False) and getattr(args, "full", None):
        raise ValueError("Use either --auth-only or --full, not both.")
    if getattr(args, "full", None) is None:
        args.full = not getattr(args, "auth_only", False)
    pull_cloud_backup_if_requested(args)
    if hasattr(args, "pre_captured_status"):
        status = args.pre_captured_status
    else:
        status = capture_and_save_current_status(args)

    archive_path = resolve_archive_path(args)
    _validate_restore_target(args, archive_path)

    _auto_backup_before_switch(args, status)

    archive_path, metadata, restored_files, safety_path = perform_restore(args)
    restored_email = str(metadata.get("email", "unknown"))
    verified_status = _validate_restored_account(args, restored_email)
    save_active_account(
        verified_status.email if verified_status is not None else restored_email,
        dry_run=args.dry_run,
    )
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
    pull_cloud_index_if_requested(args)
    backup_dir = Path(args.backup_dir).expanduser()
    entries = [
        *list_backups(backup_dir, latest_per_email=True),
        *list_status_metadata(backup_dir, latest_per_email=True),
    ]
    statuses = evaluate_entries(entries, decision_model=args.decision_model)[: args.limit]
    if args.json:
        console.print(
            json.dumps([asdict(item) for item in statuses], indent=2, default=str), markup=False
        )
    else:
        print_statuses_table(statuses)


def handle_list_backups(args: argparse.Namespace) -> None:
    if getattr(args, "cloud", False):
        import tempfile

        with tempfile.TemporaryDirectory(prefix="agm-cloud-list-") as tmp_dir:
            backup_dir = Path(tmp_dir)
            pull_cloud_index_if_requested(args, override_backup_dir=backup_dir)
            entries = list_backups(
                backup_dir,
                email=args.email,
                latest_per_email=not getattr(args, "all", False),
            )
            if args.json:
                console.print(
                    json.dumps([asdict(item) for item in entries], indent=2, default=str),
                    markup=False,
                )
            else:
                print_entries_table(entries)
    else:
        entries = list_backups(
            Path(args.backup_dir).expanduser(),
            email=args.email,
            latest_per_email=not getattr(args, "all", False),
        )
        if args.json:
            console.print(
                json.dumps([asdict(item) for item in entries], indent=2, default=str), markup=False
            )
        else:
            print_entries_table(entries)


def handle_recommend(args: argparse.Namespace) -> None:
    if args.use and args.restore:
        raise ValueError("Use either --use or --restore, not both.")
    
    captured_status = None
    if args.use or args.restore:
        try:
            captured_status = capture_and_save_current_status(args)
        except Exception as e:
            console.print(f"[warning]Failed to capture current status before recommendation: {e}[/warning]")
            
    pull_cloud_index_if_requested(args)
    backup_dir = Path(args.backup_dir).expanduser()
    entries = [
        *list_backups(backup_dir, latest_per_email=True),
        *list_status_metadata(backup_dir, latest_per_email=True),
    ]
    statuses = evaluate_entries(entries, decision_model=args.decision_model)
    if args.use or args.restore:
        current_fp = _current_token_fingerprint(args)
        if current_fp:
            filtered_statuses = []
            for status in statuses:
                try:
                    candidate_archive = resolve_archive_path(
                        argparse.Namespace(
                            backup_dir=args.backup_dir,
                            target=status.email,
                            from_archive=None,
                            email=None,
                        )
                    )
                    candidate_fp = read_token_fingerprint_from_archive(candidate_archive)
                except Exception:
                    candidate_fp = None
                if candidate_fp and candidate_fp == current_fp:
                    continue
                filtered_statuses.append(status)
            statuses = filtered_statuses
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
                    (f"available_in: {format_remaining(selected.remaining_seconds)}"),
                    f"all_models: {selected.available_models}/{selected.total_models}",
                    f"source: {selected.source}",
                ]
            )
        )
    if args.use:
        args.target = selected.email
        args.email = None
        args.full = False
        args.force = False
        args.from_archive = None
        args.pre_captured_status = captured_status
        pull_cloud_backup_if_requested(args)
        handle_use(args)
    elif args.restore:
        args.target = selected.email
        args.email = None
        args.auth_only = False
        args.full = True
        args.force = False
        args.from_archive = None
        args.pre_captured_status = captured_status
        pull_cloud_backup_if_requested(args)
        handle_restore(args)


def handle_use(args: argparse.Namespace) -> None:
    args.full = False
    args.force = False
    args.from_archive = None
    args.email = None
    pull_cloud_backup_if_requested(args)
    if hasattr(args, "pre_captured_status"):
        status = args.pre_captured_status
    else:
        status = capture_and_save_current_status(args)

    archive_path = resolve_archive_path(args)
    _validate_restore_target(args, archive_path)

    _auto_backup_before_switch(args, status)

    archive_path, metadata, restored_files, safety_path = perform_restore(args)
    restored_email = str(metadata.get("email", "unknown"))
    verified_status = _validate_restored_account(args, restored_email)
    save_active_account(
        verified_status.email if verified_status is not None else restored_email,
        dry_run=args.dry_run,
    )
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
        backup_dir=Path(args.backup_dir).expanduser(),
        args=args,
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
    console.print(
        prune_result_to_text(plan, dry_run=args.dry_run, source_dir=Path(args.source_dir))
    )





def handle_purge(args: argparse.Namespace) -> None:
    args.dry_run = getattr(args, "dry_run", False) or not getattr(args, "yes", False)
    source_dir = Path(args.source_dir).expanduser()
    success = perform_purge(args)
    console.print(purge_result_to_text(success, source_dir=source_dir, dry_run=args.dry_run))


def handle_remove(args: argparse.Namespace) -> None:
    args.dry_run = getattr(args, "dry_run", False) or not getattr(args, "yes", False)
    if getattr(args, "cloud", False):
        import tempfile

        with tempfile.TemporaryDirectory(prefix="agm-cloud-remove-") as tmp_dir:
            backup_dir = Path(tmp_dir)
            pull_cloud_index_if_requested(args, override_backup_dir=backup_dir)

            # We need to simulate the local remove but for cloud objects
            # perform_remove looks at the backup_dir to find files to delete.
            # We must override args.backup_dir temporarily for the function call.
            original_backup_dir = args.backup_dir
            args.backup_dir = str(backup_dir)
            results = perform_remove(args)
            args.backup_dir = original_backup_dir

            access_key, secret_key, bucket_name, endpoint_url = resolve_credentials(args)
            results["cloud_files_removed"] = delete_cloud_account_objects(
                email=args.email,
                bucket_name=bucket_name,
                endpoint_url=endpoint_url,
                access_key=access_key,
                secret_key=secret_key,
                dry_run=args.dry_run,
            )
            # For cloud-only mode, we don't report local files removed (which should be 0 anyway)
            console.print(remove_result_to_text(results, email=args.email, dry_run=args.dry_run))
    else:
        results = perform_remove(args)
        console.print(remove_result_to_text(results, email=args.email, dry_run=args.dry_run))


def handle_profile(args: argparse.Namespace) -> None:
    if args.action == "export":
        export_profile(Path(args.file).expanduser(), dry_run=args.dry_run)
        if not args.dry_run:
            console.print(f"Profile exported to {args.file}")
    elif args.action == "import":
        import_profile(Path(args.file).expanduser(), dry_run=args.dry_run)
        if not args.dry_run:
            console.print(f"Profile imported from {args.file}")


def handle_sync(args: argparse.Namespace) -> None:
    backup_dir = Path(args.backup_dir).expanduser()
    access_key, secret_key, bucket_name, endpoint_url = resolve_credentials(args)

    if args.direction == "push":
        push_backup(
            backup_dir=backup_dir,
            bucket_name=bucket_name,
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            dry_run=args.dry_run,
        )
    elif args.direction == "pull":
        pull_backup(
            backup_dir=backup_dir,
            bucket_name=bucket_name,
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            dry_run=args.dry_run,
        )
    elif args.direction == "auto":
        sync_auto(
            backup_dir=backup_dir,
            bucket_name=bucket_name,
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            dry_run=args.dry_run,
        )


def main() -> None:
    # Handle main help manually to use Rich
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ["-h", "--help"]):
        banner()
        print_rich_help()
        return

    parser = build_parser()
    args = parser.parse_args()

    # Branded experience for major commands
    if args.command in [
        "backup",
        "restore",
        "sync",
        "recommend",
        "status",
        "doctor",
        "prune",
        "list-backups",
    ]:
        if not getattr(args, "json", False):
            banner()

    # Handle shortcuts and default command
    if args.status:
        args.command = "status"
        # Populate defaults for status if not provided via subcommand
        if not hasattr(args, "input_file"):
            args.input_file = None
            args.backup_dir = str(DEFAULT_BACKUP_DIR)
            args.no_save = False
            args.json = False
            args.agy_command = "agy"
            args.tmux_session_name = None
            args.tmux_cols = 140
            args.tmux_rows = 45
            args.startup_timeout_seconds = 15.0
            args.usage_timeout_seconds = 15.0
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

        "purge": handle_purge,
        "remove": handle_remove,
        "rm": handle_remove,
        "profile": handle_profile,
        "sync": handle_sync,
    }
    try:
        handlers[args.command](args)
    except (FileNotFoundError, FileExistsError, ValueError, RuntimeError, AntigravityStatusError) as exc:
        error_console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
