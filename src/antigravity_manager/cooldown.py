from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import DEFAULT_DECISION_MODEL, GEMINI_HOME
from .list_backups import BackupEntry, parse_dt
from .registry import load_registry


@dataclass(frozen=True)
class ModelCooldown:
    name: str
    quota_percent_left: int | None
    is_available: bool
    refresh_at: datetime | None
    remaining_seconds: int


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


def read_active_email(gemini_home: Path = GEMINI_HOME) -> str | None:
    try:
        data = json.loads((gemini_home / "google_accounts.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    active = data.get("active")
    return active.strip() if isinstance(active, str) and active.strip() else None


def evaluate_model(model: dict[str, Any], *, now: datetime) -> ModelCooldown:
    refresh_at = (
        parse_dt(str(model.get("refresh_at"))) if isinstance(model.get("refresh_at"), str) else None
    )
    is_available = bool(model.get("is_available"))
    remaining_seconds = int((refresh_at - now).total_seconds()) if refresh_at else 0
    if is_available:
        remaining_seconds = 0
    return ModelCooldown(
        name=str(model.get("model_name") or "unknown"),
        quota_percent_left=model.get("quota_percent_left"),
        is_available=is_available,
        refresh_at=refresh_at,
        remaining_seconds=max(0, remaining_seconds),
    )


def find_decision_model(
    models: tuple[ModelCooldown, ...], model_pattern: str
) -> ModelCooldown | None:
    pattern = model_pattern.lower()
    matches = [model for model in models if pattern in model.name.lower()]
    if not matches:
        return None
    high = [model for model in matches if "(high)" in model.name.lower()]
    return high[0] if high else matches[0]


def evaluate_metadata(
    metadata: dict[str, Any],
    *,
    source: str,
    now: datetime | None = None,
    decision_model: str = DEFAULT_DECISION_MODEL,
) -> CooldownStatus:
    current = now if now is not None else datetime.now().astimezone()
    status = metadata.get("status", {}) if isinstance(metadata.get("status"), dict) else {}
    model_statuses = tuple(
        evaluate_model(model, now=current) for model in _models_from_status(status)
    )
    available_models = sum(1 for model in model_statuses if model.is_available)
    total_models = len(model_statuses)
    decision_model_status = find_decision_model(model_statuses, decision_model)
    refresh_times = [model.refresh_at for model in model_statuses if model.refresh_at is not None]
    next_available_at = (
        min(refresh_times)
        if refresh_times
        else parse_dt(str(metadata.get("next_available_at", "")))
    )
    remaining_seconds = (
        int((next_available_at - current).total_seconds()) if next_available_at else 0
    )
    if decision_model_status is not None:
        account_status = (
            "ready"
            if decision_model_status.is_available or decision_model_status.remaining_seconds <= 0
            else "cooldown"
        )
        remaining_seconds = decision_model_status.remaining_seconds
        next_available_at = (
            current if account_status == "ready" else decision_model_status.refresh_at
        )
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
    )


def evaluate_entries(
    entries: list[BackupEntry],
    *,
    now: datetime | None = None,
    decision_model: str = DEFAULT_DECISION_MODEL,
) -> list[CooldownStatus]:
    latest: dict[str, CooldownStatus] = {}
    for entry in entries:
        status = evaluate_metadata(
            entry.metadata, source="backup", now=now, decision_model=decision_model
        )
        existing = latest.get(status.email)
        if existing is None or (
            status.next_available_at is not None
            and existing.next_available_at is not None
            and status.next_available_at > existing.next_available_at
        ):
            latest[status.email] = status

    for email, record in load_registry().items():
        status = evaluate_metadata(
            record, source="registry", now=now, decision_model=decision_model
        )
        latest[email] = status

    return sorted(
        latest.values(),
        key=lambda item: (item.status != "ready", item.remaining_seconds, item.email),
    )


def format_model_usage(model: ModelCooldown) -> str:
    quota = f"{model.quota_percent_left}%" if model.quota_percent_left is not None else "unknown"
    if model.is_available:
        state = "Ready"
    else:
        state = compact_remaining(model.remaining_seconds)
    return f"{compact_model_name(model.name)}  {quota}  {color_for_model(model, state)}"


def color_for_model(model: ModelCooldown, text: str) -> str:
    percent = model.quota_percent_left
    if percent is None:
        return f"[dim]{text}[/]"
    if percent >= 50:
        return f"[green]{text}[/]"
    if percent >= 20:
        return f"[yellow]{text}[/]"
    if percent > 0:
        return f"[dark_orange]{text}[/]"
    return f"[red]{text}[/]"


def compact_model_name(name: str) -> str:
    replacements = {
        "Gemini 3.5 Flash": "G3.5F",
        "Gemini 3.1 Pro": "G3.1P",
        "Claude Sonnet 4.6": "Son4.6",
        "Claude Opus 4.6": "Opus4.6",
        "GPT-OSS 120B": "GPT120B",
        "(Thinking)": "Think",
        "(Medium)": "Med",
        "(High)": "High",
        "(Low)": "Low",
    }
    compact = name
    for old, new in replacements.items():
        compact = compact.replace(old, new)
    return " ".join(compact.split())


def compact_remaining(seconds: int) -> str:
    return format_remaining(seconds).replace(" ", "")


def print_statuses_table(statuses: list[CooldownStatus]) -> None:
    from .ui import Panel, Table, console

    active_email = read_active_email()
    table = Table(show_header=True, header_style="bold bright_magenta")
    table.add_column("Account", style="bright_cyan")
    table.add_column("Status", justify="center")
    table.add_column("Usage")
    table.add_column("Next Reset", justify="right", style="dim")

    for status in statuses:
        if status.email == active_email:
            status_text = "[bold bright_green]ACTIVE[/]"
        elif status.status == "ready":
            status_text = "[bold bright_green]READY[/]"
        else:
            status_text = "[bold bright_yellow]COOLDOWN[/]"

        usage = "\n".join(format_model_usage(model) for model in status.models) or "unknown"
        next_available = format_remaining(status.remaining_seconds)
        table.add_row(
            status.email,
            status_text,
            usage,
            next_available,
        )
    console.print(
        Panel(
            table,
            title="[bold bright_cyan]Antigravity Cooldown[/]",
            border_style="bright_cyan",
            expand=False,
        )
    )
