from __future__ import annotations

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
    GEMINI_HOME,
    GEMINI_IDENTITY_FILES,
)
from .registry import update_registry_from_status
from .status import LiveStatus, capture_tmux_status_text, parse_live_status_text, status_to_dict
from .utils import build_archive_name, isoformat_local

ESTIMATED_MODEL_RESET_HOURS = 5


def find_decision_model(
    status: LiveStatus, model_pattern: str = DEFAULT_DECISION_MODEL
) -> Any | None:
    pattern = model_pattern.lower()
    matches = [model for model in status.models if pattern in model.model_name.lower()]
    if not matches:
        return None
    high = [model for model in matches if "(high)" in model.model_name.lower()]
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
            "estimated_5h_decision_model_available",
            model.model_name,
        )

    refreshes = [item.refresh_at for item in status.models if item.refresh_at is not None]
    if refreshes:
        return max(refreshes), "latest_model_refresh_at", model.model_name if model else None

    return (
        status.captured_at + timedelta(hours=ESTIMATED_MODEL_RESET_HOURS),
        "estimated_5h_no_model_reset_in_usage",
        model.model_name if model else None,
    )


def read_active_email(gemini_home: Path = GEMINI_HOME) -> str | None:
    path = gemini_home / "google_accounts.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    active = data.get("active")
    return active.strip() if isinstance(active, str) and active.strip() else None


def fallback_status(email: str | None) -> LiveStatus:
    from .status import ModelQuotaStatus

    now = datetime.now().astimezone()
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
                refresh_in_text="Status capture bypassed; estimated 5h cooldown",
                refresh_at=reset_at,
                is_available=False,
            ),
        ),
    )


def get_status_for_backup(args: Any) -> LiveStatus:
    if getattr(args, "without_status_check", False):
        return fallback_status(read_active_email(Path(args.gemini_home).expanduser()))
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
    source_gemini_home: Path,
    backup_mode: str,
    include_bin: bool,
    include_logs: bool,
    decision_model: str,
    backup_anchor_at: datetime,
    backup_anchor_source: str,
    backup_anchor_model: str | None,
) -> dict[str, Any]:
    next_refreshes = [model.refresh_at for model in status.models if model.refresh_at is not None]
    next_available_at = (
        max(next_refreshes).isoformat() if next_refreshes else status.captured_at.isoformat()
    )
    return {
        "schema_version": 1,
        "product": "antigravity",
        "email": status.email,
        "plan": status.plan,
        "created_at": isoformat_local(datetime.now().astimezone()),
        "captured_at": isoformat_local(status.captured_at),
        "next_available_at": next_available_at,
        "decision_model": decision_model,
        "backup_anchor_at": isoformat_local(backup_anchor_at),
        "backup_anchor_source": backup_anchor_source,
        "backup_anchor_model": backup_anchor_model,
        "archive_name": archive_path.name,
        "archive_path": str(archive_path),
        "source_antigravity_home": str(source_antigravity_home),
        "source_gemini_home": str(source_gemini_home),
        "backup_mode": backup_mode,
        "include_bin": include_bin,
        "include_logs": include_logs,
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


def iter_gemini_identity_entries(gemini_home: Path) -> list[Path]:
    return [gemini_home / name for name in GEMINI_IDENTITY_FILES if (gemini_home / name).exists()]


def create_backup_archive(
    *,
    archive_path: Path,
    metadata_path: Path,
    metadata: dict[str, Any],
    antigravity_home: Path,
    gemini_home: Path,
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

        with tarfile.open(archive_path, "w:gz") as tar:
            for path in iter_antigravity_entries(
                antigravity_home,
                auth_only=auth_only,
                include_bin=include_bin,
                include_logs=include_logs,
            ):
                tar.add(path, arcname=f"antigravity-cli/{path.name}", recursive=True)
            for path in iter_gemini_identity_entries(gemini_home):
                tar.add(path, arcname=f"gemini/{path.name}", recursive=False)
            tar.add(temp_metadata_path, arcname=temp_metadata_path.name, recursive=False)


def perform_backup(args: Any) -> tuple[Path, Path, dict[str, Any]]:
    antigravity_home = Path(args.source_dir).expanduser()
    gemini_home = Path(args.gemini_home).expanduser()
    if not antigravity_home.is_dir():
        raise FileNotFoundError(f"Antigravity directory does not exist: {antigravity_home}")

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
        source_gemini_home=gemini_home,
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
        gemini_home=gemini_home,
        auth_only=getattr(args, "auth_only", False),
        include_bin=getattr(args, "include_bin", False),
        include_logs=getattr(args, "include_logs", False),
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    latest_path = backup_dir / f"{status.email}-latest-antigravity.tar.gz"
    if latest_path.exists() or latest_path.is_symlink():
        latest_path.unlink()
    latest_path.symlink_to(archive_path.name)
    update_registry_from_status(status)
    return archive_path, metadata_path, metadata


def backup_result_to_text(
    archive_path: Path, metadata_path: Path, metadata: dict[str, Any], *, dry_run: bool
) -> str:
    return "\n".join(
        [
            f"mode: {'dry-run' if dry_run else 'created'}",
            f"archive: {archive_path}",
            f"metadata: {metadata_path}",
            f"email: {metadata.get('email', 'unknown')}",
            f"plan: {metadata.get('plan', 'unknown')}",
            f"next_available_at: {metadata.get('next_available_at', 'unknown')}",
            f"backup_anchor: {metadata.get('backup_anchor_at', 'unknown')} ({metadata.get('backup_anchor_source', 'unknown')})",
            f"backup_mode: {metadata.get('backup_mode', 'unknown')}",
        ]
    )
