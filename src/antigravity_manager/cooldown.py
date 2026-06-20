from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .config import DEFAULT_DECISION_MODEL
from .list_backups import BackupEntry, parse_dt
from .registry import load_registry
from .utils import read_active_email


@dataclass(frozen=True)
class ModelCooldown:
    name: str
    quota_percent_left: int | None
    is_available: bool
    refresh_at: datetime | None
    remaining_seconds: int
    block_reason: str | None = None


@dataclass(frozen=True)
class CooldownStatus:
    email: str
    plan: str
    status: str
    available_models: int
    total_models: int
    next_available_at: datetime | None
    remaining_seconds: int
    source: str
    decision_model: str
    decision_model_status: ModelCooldown | None
    models: tuple[ModelCooldown, ...]
    last_checked_at: datetime | None = None


def format_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "now"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _models_from_status(status: dict[str, Any]) -> list[dict[str, Any]]:
    models = status.get("models", [])
    return models if isinstance(models, list) else []


def evaluate_model(model: dict[str, Any], *, now: datetime) -> ModelCooldown:
    if now.tzinfo is None:
        now = now.astimezone()

    refresh_at = (
        parse_dt(str(model.get("refresh_at"))) if isinstance(model.get("refresh_at"), str) else None
    )
    is_available = bool(model.get("is_available"))
    block_reason = model.get("block_reason")
    if block_reason is not None:
        block_reason = str(block_reason)
    
    # parse_dt now returns aware dt. Ensure both are aware.
    remaining_seconds = int((refresh_at - now).total_seconds()) if refresh_at else 0
    if is_available:
        remaining_seconds = 0
    return ModelCooldown(
        name=str(model.get("model_name") or "unknown"),
        quota_percent_left=model.get("quota_percent_left"),
        is_available=is_available,
        refresh_at=refresh_at,
        remaining_seconds=max(0, remaining_seconds),
        block_reason=block_reason,
    )


def find_decision_model(
    models: tuple[ModelCooldown, ...], model_pattern: str
) -> ModelCooldown | None:
    pattern = model_pattern.lower()
    matches = [model for model in models if pattern in model.name.lower()]
    
    # Fuzzy fallback for new layout
    if not matches:
        if "gemini" in pattern:
            matches = [m for m in models if "gemini" in m.name.lower()]
        elif "claude" in pattern:
            matches = [m for m in models if "claude" in m.name.lower()]
        elif "gpt" in pattern:
            matches = [m for m in models if "gpt" in m.name.lower()]
            
    if not matches:
        return None
        
    # Prefer High/Pro tiers if multiple matches
    high = [model for model in matches if any(x in model.name.lower() for x in ("(high)", "pro"))]
    return high[0] if high else matches[0]


def evaluate_metadata(
    metadata: dict[str, Any],
    *,
    source: str,
    now: datetime | None = None,
    decision_model: str = DEFAULT_DECISION_MODEL,
) -> CooldownStatus:
    current = now if now is not None else datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.astimezone()
    status = metadata.get("status", {}) if isinstance(metadata.get("status"), dict) else {}
    last_checked_at = parse_dt(str(metadata.get("captured_at", ""))) or parse_dt(
        str(metadata.get("created_at", ""))
    )
    model_statuses = tuple(
        evaluate_model(model, now=current) for model in _models_from_status(status)
    )
    available_models = sum(1 for model in model_statuses if model.is_available)
    total_models = len(model_statuses)
    decision_model_status = find_decision_model(model_statuses, decision_model)
    has_blocked_model = any(model.block_reason for model in model_statuses)
    refresh_times = [model.refresh_at for model in model_statuses if model.refresh_at is not None]
    next_available_at = (
        min(refresh_times)
        if refresh_times
        else parse_dt(str(metadata.get("next_available_at", "")))
    )
    # Ensure next_available_at and current have same awareness
    if next_available_at and (next_available_at.tzinfo is None) != (current.tzinfo is None):
        if next_available_at.tzinfo is None:
            next_available_at = next_available_at.astimezone()
        else:
            current = current.astimezone()

    remaining_seconds = (
        int((next_available_at - current).total_seconds()) if next_available_at else 0
    )
    if decision_model_status is not None:
        if decision_model_status.block_reason:
            account_status = "blocked"
        else:
            account_status = (
                "ready"
                if decision_model_status.is_available or decision_model_status.remaining_seconds <= 0
                else "cooldown"
            )
        remaining_seconds = decision_model_status.remaining_seconds
        next_available_at = (
            current if account_status == "ready" else decision_model_status.refresh_at
        )
    elif has_blocked_model:
        account_status = "blocked"
    else:
        account_status = "ready" if available_models > 0 or remaining_seconds <= 0 else "cooldown"
    if account_status == "ready":
        remaining_seconds = 0
        next_available_at = current
    return CooldownStatus(
        email=metadata.get("email", "unknown"),
        plan=metadata.get("plan", "unknown"),
        status=account_status,
        available_models=available_models,
        total_models=total_models,
        next_available_at=next_available_at,
        remaining_seconds=max(0, remaining_seconds),
        source=source,
        decision_model=decision_model,
        decision_model_status=decision_model_status,
        models=model_statuses,
        last_checked_at=last_checked_at,
    )


def evaluate_entries(
    entries: list[BackupEntry],
    *,
    now: datetime | None = None,
    decision_model: str = DEFAULT_DECISION_MODEL,
) -> list[CooldownStatus]:
    latest: dict[str, CooldownStatus] = {}
    latest_seen_at: dict[str, datetime] = {}
    for entry in entries:
        if entry.email == "unknown":
            continue
        status = evaluate_metadata(
            entry.metadata, source=entry.source, now=now, decision_model=decision_model
        )
        if status.email == "unknown":
            continue
        seen_at = parse_dt(entry.captured_at) or parse_dt(entry.created_at) or datetime.min
        existing = latest.get(status.email)
        if existing is None or seen_at >= latest_seen_at.get(status.email, datetime.min):
            latest[status.email] = status
            latest_seen_at[status.email] = seen_at

    for email, record in load_registry().items():
        if email == "unknown":
            continue
        if "email" not in record:
            record = dict(record)
            record["email"] = email
        status = evaluate_metadata(
            record, source="registry", now=now, decision_model=decision_model
        )
        if status.email == "unknown":
            continue
        latest[email] = status

    status_priority = {"ready": 0, "cooldown": 1, "blocked": 2}
    return sorted(
        latest.values(),
        key=lambda item: (
            status_priority.get(item.status, 3),
            item.remaining_seconds,
            item.last_checked_at.timestamp() if item.last_checked_at else float("inf"),
            item.email,
        ),
    )



def format_model_usage(model: ModelCooldown) -> str:
    # Get color and formatted quota
    quota_val = model.quota_percent_left
    quota_str = f"{quota_val}%" if quota_val is not None else "unknown"
    
    # Determine color
    if quota_val is None:
        color = "dim"
    elif quota_val >= 75:
        color = "spring_green3"
    elif quota_val >= 50:
        color = "yellow3"
    elif quota_val >= 25:
        color = "dark_orange"
    else:
        color = "red3"
    
    # Format components
    # model name: dim white, fixed width for alignment if possible, here using string padding
    name_str = f"[dim white]{compact_model_name(model.name):<8}[/]"
    # quota: fixed width (6), right aligned
    quota_str = f"[{color}]{quota_str:>{4}}[/]"
    
    # State/Refresh
    if model.is_available:
        rem_sec = 0
        if model.refresh_at:
            tz = model.refresh_at.tzinfo
            now = datetime.now(tz) if tz else datetime.now().astimezone()
            rem_sec = max(0, int((model.refresh_at - now).total_seconds()))
        if rem_sec > 0:
            state = f"[dim]Ready ({compact_remaining(rem_sec)})[/]"
        else:
            state = "[success]Ready[/]"
    elif model.block_reason:
        state = "[bold red]Blocked[/]"
    else:
        state = f"[dim]{compact_remaining(model.remaining_seconds)}[/]"
        
    return f"{name_str} {quota_str} {state}"


def color_for_model(model: ModelCooldown, text: str) -> str:
    percent = model.quota_percent_left
    if percent is None:
        return f"[dim]{text}[/]"
    if percent >= 75:
        return f"[spring_green3]{text}[/]"
    if percent >= 50:
        return f"[yellow3]{text}[/]"
    if percent >= 25:
        return f"[dark_orange]{text}[/]"
    return f"[red3]{text}[/]"


def compact_model_name(name: str) -> str:
    replacements = {
        "GEMINI MODELS": "Gemini",
        "CLAUDE AND GPT MODELS": "Claude",
    }
    compact = name
    for old, new in replacements.items():
        if old in compact:
            return new
            
    # Fallback for individual models if they aren't grouped yet
    individual_replacements = {
        "Gemini 3.5 Flash": "Gemini",
        "Gemini 3.1 Pro": "Gemini",
        "Claude Sonnet 4.6": "Claude",
        "Claude Opus 4.6": "Claude",
        "GPT-OSS 120B": "GPT",
    }
    for old, new in individual_replacements.items():
        if old in compact:
            return new

    return compact.split("(")[0].strip()


def compact_remaining(seconds: int) -> str:
    return format_remaining(seconds).replace(" ", "")


def format_age(checked_at: datetime | None, *, now: datetime | None = None) -> str:
    if checked_at is None:
        return "-"
    current = now if now is not None else datetime.now().astimezone()
    
    # Normalize awareness
    if checked_at.tzinfo is None:
        checked_at = checked_at.astimezone()
    if current.tzinfo is None:
        current = current.astimezone()
        
    seconds = max(0, int((current - checked_at).total_seconds()))
    if seconds < 60:
        return f"{seconds}s ago"
    minutes, _ = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours, _ = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h ago"
    days, _ = divmod(hours, 24)
    return f"{days}d ago"


def group_models(models: tuple[ModelCooldown, ...]) -> list[ModelCooldown]:
    """Groups models that share identical quota and refresh times to reduce clutter."""
    if not models:
        return []

    # Map state key to list of models
    key_map: dict[tuple[int | None, int], list[ModelCooldown]] = {}
    # Track order of first appearance
    ordered_keys: list[tuple[int | None, int]] = []

    for m in models:
        key = (m.quota_percent_left, m.remaining_seconds)
        if key not in key_map:
            key_map[key] = []
            ordered_keys.append(key)
        key_map[key].append(m)

    result: list[ModelCooldown] = []
    for key in ordered_keys:
        members = key_map[key]
        if len(members) == 1:
            result.append(members[0])
            continue

        # Pick a representative for the group
        # Preference: (High) > (Thinking) > first one
        rep = members[0]
        highs = [m for m in members if "(high)" in m.name.lower()]
        thinks = [m for m in members if "(thinking)" in m.name.lower()]

        if highs:
            rep = highs[0]
        elif thinks:
            rep = thinks[0]

        result.append(rep)

    return result


def print_statuses_table(statuses: list[CooldownStatus]) -> None:
    from .ui import Panel, Table, console

    active_email = read_active_email()
    table = Table(show_header=True, header_style="bold bright_magenta")
    table.add_column("Account", style="bright_cyan")
    table.add_column("Status", justify="center")
    table.add_column("Usage")
    table.add_column("Last Checked", justify="right", style="dim")

    for status in statuses:
        if status.email == "unknown":
            continue
        if status.status == "blocked":
            status_text = "[bold red]BLOCKED[/]"
        elif status.email == active_email:
            status_text = "[bold bright_blue]ACTIVE[/]"
        elif status.status == "ready":
            status_text = "[bold bright_green]READY[/]"
        else:
            status_text = "[bold bright_yellow]COOLDOWN[/]"

        display_models = group_models(status.models)
        usage = "\n".join(format_model_usage(model) for model in display_models) or "unknown"
        last_checked = format_age(status.last_checked_at)
        table.add_row(
            status.email,
            status_text,
            usage,
            last_checked,
        )
    console.print(
        Panel(
            table,
            title="[bold bright_cyan]Antigravity Cooldown[/]",
            border_style="bright_cyan",
            expand=False,
        )
    )
