from __future__ import annotations

import hashlib
import json
import tarfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import (
    ANTIGRAVITY_AUTH_FILES,
    DEFAULT_DECISION_MODEL,
    EXCLUDED_TOP_LEVEL_NAMES,
)
from .registry import update_registry_from_status
from .status import LiveStatus, capture_tmux_status_text, parse_live_status_text, status_to_dict
from .ui import RenderableType
from .utils import build_archive_name, isoformat_local, read_active_email

ESTIMATED_MODEL_RESET_HOURS = 5

# Salt is not secret (no HMAC secret needed here). We just want a stable,
# non-reversible fingerprint of the refresh_token so we can detect when two
# archives (or the live credential) share the same underlying Google account.
_TOKEN_FINGERPRINT_SALT = b"agm-token-fingerprint-v1"


def _compute_token_fingerprint(refresh_token: str) -> str:
    """Return a stable hex fingerprint of a refresh_token."""
    h = hashlib.sha256(_TOKEN_FINGERPRINT_SALT + refresh_token.encode())
    return h.hexdigest()[:16]


def read_token_fingerprint_from_path(token_path: Path) -> str | None:
    """Read the antigravity-oauth-token file and return its fingerprint, or None."""
    try:
        data = json.loads(token_path.read_bytes())
        rt = data.get("token", {}).get("refresh_token", "")
        return _compute_token_fingerprint(rt) if rt else None
    except Exception:
        return None


def read_token_fingerprint_from_archive(archive_path: Path) -> str | None:
    """Extract antigravity-oauth-token from a .tar.gz archive and return its fingerprint."""
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            member = tar.getmember("antigravity-cli/antigravity-oauth-token")
            f = tar.extractfile(member)
            if f is None:
                return None
            data = json.load(f)
            rt = data.get("token", {}).get("refresh_token", "")
            return _compute_token_fingerprint(rt) if rt else None
    except Exception:
        return None


def find_decision_model(
    status: LiveStatus, model_pattern: str = DEFAULT_DECISION_MODEL
) -> Any | None:
    pattern = model_pattern.lower()
    matches = [model for model in status.models if pattern in model.model_name.lower()]
    
    # Fuzzy fallback for new layout if no exact match (e.g., matching "Gemini" in "GEMINI MODELS")
    if not matches:
        if "gemini" in pattern:
            matches = [m for m in status.models if "gemini" in m.model_name.lower()]
        elif "claude" in pattern:
            matches = [m for m in status.models if "claude" in m.model_name.lower()]
        elif "gpt" in pattern:
            matches = [m for m in status.models if "gpt" in m.model_name.lower()]

    if not matches:
        return None
        
    # Prefer High/Pro tiers if multiple matches
    high = [model for model in matches if any(x in model.model_name.lower() for x in ("(high)", "pro"))]
    return high[0] if high else matches[0]


def resolve_backup_anchor(
    status: LiveStatus, model_pattern: str = DEFAULT_DECISION_MODEL
) -> tuple[datetime, str, str | None]:
    model = find_decision_model(status, model_pattern)
    if model and model.refresh_at is not None:
        return model.refresh_at, "decision_model_refresh_at", model.model_name
    if model and model.is_available:
        return (
            status.captured_at + timedelta(hours=ESTIMATED_MODEL_RESET_HOURS),
            f"estimated_{ESTIMATED_MODEL_RESET_HOURS}h_decision_model_available",
            model.model_name,
        )

    refreshes = [item.refresh_at for item in status.models if item.refresh_at is not None]
    if refreshes:
        return max(refreshes), "latest_model_refresh_at", model.model_name if model else None

    return (
        status.captured_at + timedelta(hours=ESTIMATED_MODEL_RESET_HOURS),
        f"estimated_{ESTIMATED_MODEL_RESET_HOURS}h_no_model_reset_in_usage",
        model.model_name if model else None,
    )


def fallback_status(email: str | None) -> LiveStatus:
    from .registry import load_registry
    from .status import ModelQuotaStatus, parse_live_status_text

    now = datetime.now().astimezone()
    
    # Try to recover the last known status from the registry to preserve real cooldowns
    if email:
        registry = load_registry()
        if email in registry:
            reg_entry = registry[email]
            status_data = reg_entry.get("status")
            if status_data:
                from .list_backups import parse_dt
                models = []
                for m in status_data.get("models", []):
                    model_name = m.get("model_name", "unknown")
                    # If the registry only has "unknown" or "bypassed" status, ignore it
                    if model_name == "unknown" or "bypassed" in str(m.get("refresh_in_text", "")):
                        models = []
                        break
                        
                    refresh_at_str = m.get("refresh_at")
                    refresh_at = parse_dt(refresh_at_str) if refresh_at_str else None
                    
                    models.append(ModelQuotaStatus(
                        model_name=model_name,
                        quota_percent_left=m.get("quota_percent_left"),
                        refresh_in_text=m.get("refresh_in_text"),
                        refresh_at=refresh_at,
                        is_available=m.get("is_available", False),
                        block_reason=m.get("block_reason"),
                    ))
                
                if models:
                    return LiveStatus(
                        email=email,
                        plan=reg_entry.get("plan", "unknown"),
                        is_pro=reg_entry.get("is_pro", False),
                        captured_at=parse_dt(reg_entry.get("captured_at")) or now,
                        models=tuple(models)
                    )

    # Worst-case fallback: Assume a fresh weekly reset (168h)
    reset_at = now + timedelta(hours=ESTIMATED_MODEL_RESET_HOURS)
    return LiveStatus(
        email=email or "unknown",
        plan="unknown",
        is_pro=False,
        captured_at=now,
        models=(
            ModelQuotaStatus(
                model_name="unknown",
                quota_percent_left=None,
                refresh_in_text=f"Status capture bypassed; estimated {ESTIMATED_MODEL_RESET_HOURS}h cooldown",
                refresh_at=reset_at,
                is_available=False,
            ),
        ),

    )


def get_status_for_backup(args: Any) -> LiveStatus:
    if getattr(args, "no_status", False):
        return fallback_status(read_active_email(Path(args.source_dir).expanduser()))
    if getattr(args, "status_file", None):
        text = Path(args.status_file).expanduser().read_text(encoding="utf-8")
    else:
        text = capture_tmux_status_text(
            session_name=getattr(args, "tmux_session_name", None),
            agy_command=getattr(args, "agy_command", "agy"),
            cols=getattr(args, "tmux_cols", 140),
            rows=getattr(args, "tmux_rows", 45),
            startup_timeout_seconds=getattr(args, "startup_timeout_seconds", 30.0),
            usage_timeout_seconds=getattr(args, "usage_timeout_seconds", 30.0),
        )
    return parse_live_status_text(text)


def build_backup_metadata(
    status: LiveStatus,
    archive_path: Path,
    *,
    source_antigravity_home: Path,
    backup_mode: str,
    include_bin: bool,
    include_logs: bool,
    decision_model: str,
    backup_anchor_at: datetime,
    backup_anchor_source: str,
    backup_anchor_model: str | None,
) -> dict[str, Any]:
    # Gemini-aware readiness (mirrors cli.py/registry.py logic)
    next_available_at_dt = status.captured_at
    gemini_models = [m for m in status.models if "gemini" in m.model_name.lower() and "flash" in m.model_name.lower()]
    if gemini_models and gemini_models[0].refresh_at:
        next_available_at_dt = gemini_models[0].refresh_at
    else:
        refreshes = [m.refresh_at for m in status.models if m.refresh_at is not None]
        if refreshes:
            next_available_at_dt = max(refreshes)

    # Compute a fingerprint of the token on disk so we can detect later if two
    # archives share the same underlying credential (same Google account).
    token_path = source_antigravity_home / "antigravity-oauth-token"
    token_fingerprint = read_token_fingerprint_from_path(token_path)

    return {
        "schema_version": 1,
        "product": "antigravity",
        "email": status.email,
        "plan": status.plan,
        "created_at": isoformat_local(datetime.now().astimezone()),
        "captured_at": isoformat_local(status.captured_at),
        "next_available_at": isoformat_local(next_available_at_dt),
        "decision_model": decision_model,
        "backup_anchor_at": isoformat_local(backup_anchor_at),
        "backup_anchor_source": backup_anchor_source,
        "backup_anchor_model": backup_anchor_model,
        "archive_name": archive_path.name,
        "archive_path": str(archive_path),
        "source_antigravity_home": str(source_antigravity_home),
        "backup_mode": backup_mode,
        "include_bin": include_bin,
        "include_logs": include_logs,
        "token_fingerprint": token_fingerprint,
        "status": status_to_dict(status),
    }


def iter_antigravity_entries(
    source_dir: Path, *, auth_only: bool, include_bin: bool, include_logs: bool
) -> list[Path]:
    if auth_only:
        return [
            source_dir / name for name in ANTIGRAVITY_AUTH_FILES if (source_dir / name).exists()
        ]

    entries = []
    for path in sorted(source_dir.iterdir(), key=lambda item: item.name):
        if path.name == "bin" and not include_bin:
            continue
        if path.name == "log" and not include_logs:
            continue
        if path.name in EXCLUDED_TOP_LEVEL_NAMES and path.name != "log":
            continue
        entries.append(path)
    return entries


def create_backup_archive(
    *,
    archive_path: Path,
    metadata_path: Path,
    metadata: dict[str, Any],
    antigravity_home: Path,
    auth_only: bool,
    include_bin: bool,
    include_logs: bool,
) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agm-backup-") as temp_dir_str:
        temp_metadata_path = Path(temp_dir_str) / metadata_path.name
        temp_metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
        )

        def tar_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
            if tarinfo.name.endswith("-wal") or tarinfo.name.endswith("-shm") or tarinfo.name.endswith(".lock"):
                return None
            return tarinfo

        with tarfile.open(archive_path, "w:gz") as tar:
            def _add_safe(path_to_add: Path, arc_name: str) -> None:
                if not path_to_add.exists():
                    return
                try:
                    tar.add(
                        path_to_add,
                        arcname=arc_name,
                        recursive=False,
                        filter=tar_filter,
                    )
                except OSError:
                    # Ignore read errors (e.g., unexpected end of data) if a file
                    # is truncated or deleted concurrently during the backup process.
                    return

                if path_to_add.is_dir():
                    try:
                        children = list(path_to_add.iterdir())
                    except OSError:
                        return
                    for child in children:
                        _add_safe(child, f"{arc_name}/{child.name}")

            for path in iter_antigravity_entries(
                antigravity_home,
                auth_only=auth_only,
                include_bin=include_bin,
                include_logs=include_logs,
            ):
                _add_safe(path, f"antigravity-cli/{path.relative_to(antigravity_home)}")
            tar.add(temp_metadata_path, arcname=temp_metadata_path.name, recursive=False)


def perform_backup(args: Any, status: LiveStatus | None = None) -> tuple[Path, Path, dict[str, Any]]:
    antigravity_home = Path(args.source_dir).expanduser()
    if not antigravity_home.is_dir():
        raise FileNotFoundError(f"Antigravity directory does not exist: {antigravity_home}")

    token_path = antigravity_home / "antigravity-oauth-token"
    if not token_path.exists():
        raise FileNotFoundError(
            f"No active account found. Backup aborted because 'antigravity-oauth-token' "
            f"does not exist in {antigravity_home}."
        )

    if status is None:
        status = get_status_for_backup(args)
    backup_dir = Path(args.backup_dir).expanduser()
    decision_model = getattr(args, "decision_model", DEFAULT_DECISION_MODEL)
    backup_anchor_at, backup_anchor_source, backup_anchor_model = resolve_backup_anchor(
        status, decision_model
    )
    archive_path = backup_dir / build_archive_name(backup_anchor_at, status.email)
    metadata_path = archive_path.with_name(archive_path.name.replace(".tar.gz", ".metadata.json"))
    metadata = build_backup_metadata(
        status,
        archive_path,
        source_antigravity_home=antigravity_home,
        backup_mode="auth-only" if getattr(args, "auth_only", False) else "full",
        include_bin=getattr(args, "include_bin", False),
        include_logs=getattr(args, "include_logs", False),
        decision_model=decision_model,
        backup_anchor_at=backup_anchor_at,
        backup_anchor_source=backup_anchor_source,
        backup_anchor_model=backup_anchor_model,
    )

    if getattr(args, "dry_run", False):
        return archive_path, metadata_path, metadata

    if archive_path.exists() and not getattr(args, "force", False):
        raise FileExistsError(f"Archive already exists: {archive_path}. Use --force to overwrite.")
    if archive_path.exists():
        archive_path.unlink()
    if metadata_path.exists():
        metadata_path.unlink()

    create_backup_archive(
        archive_path=archive_path,
        metadata_path=metadata_path,
        metadata=metadata,
        antigravity_home=antigravity_home,
        auth_only=getattr(args, "auth_only", False),
        include_bin=getattr(args, "include_bin", False),
        include_logs=getattr(args, "include_logs", False),
    )

    if getattr(args, "encrypt", False):
        import getpass
        import subprocess

        import antigravity_manager.ui

        antigravity_manager.ui.console.print(f"Encrypting archive: {archive_path} -> .gpg")
        import os

        passphrase = os.environ.get("AGM_BACKUP_PASSWORD")
        if not passphrase:
            passphrase = getpass.getpass("Enter passphrase for backup encryption: ")

        if not passphrase:
            raise ValueError("Encryption requested but no passphrase provided.")

        encrypted_path = archive_path.with_suffix(archive_path.suffix + ".gpg")
        gpg_cmd = [
            "gpg",
            "--symmetric",
            "--cipher-algo",
            "AES256",
            "--passphrase-fd",
            "0",
            "--batch",
            "--yes",
            "--output",
            str(encrypted_path),
            str(archive_path),
        ]
        try:
            subprocess.run(gpg_cmd, input=passphrase.encode(), check=True)
            archive_path.unlink()
            archive_path = encrypted_path
            metadata["archive_name"] = archive_path.name
            metadata["archive_path"] = str(archive_path)
            metadata["encrypted"] = True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(f"GPG encryption failed: {e}") from e

    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    update_registry_from_status(status)
    return archive_path, metadata_path, metadata


def backup_result_to_text(
    archive_path: Path, metadata_path: Path, metadata: dict[str, Any], *, dry_run: bool
) -> RenderableType:
    from .ui import Panel, Table

    title = "[warning]Backup Result (Dry Run)[/]" if dry_run else "[success]Backup Created[/]"
    border_style = "warning" if dry_run else "success"

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", justify="right")
    table.add_column(style="white")

    table.add_row("Email:", str(metadata.get("email", "unknown")))
    table.add_row("Plan:", str(metadata.get("plan", "unknown")))
    table.add_row("Archive:", str(archive_path))
    table.add_row("Metadata:", str(metadata_path))
    table.add_row("Next Available:", str(metadata.get("next_available_at", "unknown")))

    anchor_src = metadata.get("backup_anchor_source", "unknown")
    table.add_row(
        "Anchor:",
        f"{metadata.get('backup_anchor_at', 'unknown')} [dim]({anchor_src})[/dim]",
    )
    table.add_row("Mode:", str(metadata.get("backup_mode", "unknown")))

    return Panel(table, title=title, border_style=border_style, expand=False)
