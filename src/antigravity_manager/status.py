from __future__ import annotations

import os
import re
import subprocess
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from .ui import RenderableType, console

EMAIL_AND_PLAN_RE = re.compile(
    r"(?P<email>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?:\s*\((?P<plan>[^)]+)\))?",
    re.IGNORECASE,
)
QUOTA_PERCENT_RE = re.compile(r"(\d+)%")
REFRESH_RE = re.compile(
    r"Refreshes in\s+(?:(?P<hours>\d+)h)?\s*(?:(?P<minutes>\d+)m)?",
    re.IGNORECASE,
)
PROMPT_RE = re.compile(r"[›>]")
LOGIN_PROMPT_RE = re.compile(r"Welcome to the Antigravity CLI\. You are currently not signed in\.", re.IGNORECASE)
ONBOARDING_PROMPT_RE = re.compile(r"Welcome to Antigravity CLI!.*Choose your color scheme", re.IGNORECASE | re.DOTALL)
USAGE_HEADER_RE = re.compile(r"Model Quota", re.IGNORECASE)
MODEL_NAME_RE = re.compile(r"^(?![│└>])(?=.*\()(?=.*\))(?=.*[A-Za-z]).+$")
TRUST_PROMPT_RE = re.compile(r"Do you trust the contents of this project\?", re.IGNORECASE)


class AntigravityStatusError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelQuotaStatus:
    model_name: str
    quota_percent_left: int | None
    refresh_in_text: str | None
    refresh_at: datetime | None
    is_available: bool


@dataclass(frozen=True)
class LiveStatus:
    email: str
    plan: str
    is_pro: bool
    captured_at: datetime
    models: tuple[ModelQuotaStatus, ...]


def status_to_dict(status: LiveStatus) -> dict[str, Any]:
    data = asdict(status)
    data["captured_at"] = status.captured_at.isoformat()
    for model in data["models"]:
        if model["refresh_at"] is not None:
            model["refresh_at"] = model["refresh_at"].isoformat()
    return data


def run_command(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise AntigravityStatusError(
            f"Command failed: {' '.join(args)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def verify_tmux_available() -> None:
    try:
        subprocess.run(["tmux", "-V"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise AntigravityStatusError("tmux is required for Antigravity status capture.") from None


def capture_pane(pane_id: str) -> str:
    return run_command(["tmux", "capture-pane", "-t", pane_id, "-p"]).stdout


def wait_for_prompt(pane_id: str, *, timeout_seconds: float) -> str:
    start = time.time()
    stable_reads = 0
    login_reads = 0
    onboarding_reads = 0

    with console.status("[cyan]Waiting for Antigravity startup...[/cyan]", spinner="dots"):
        while True:
            output = capture_pane(pane_id)

            # 1. Handle directory trust prompt (immediate action)
            if TRUST_PROMPT_RE.search(output):
                run_command(["tmux", "send-keys", "-t", pane_id, "Enter"], check=False)
                time.sleep(1)
                continue

            # 2. Check for successful startup (Prompt + Account)
            has_prompt = PROMPT_RE.search(output) is not None
            has_account = EMAIL_AND_PLAN_RE.search(output) is not None

            if has_prompt and has_account:
                stable_reads += 1
                if stable_reads >= 3:
                    return output
            else:
                stable_reads = 0

                # 3. Check for Login Required state (Require stability to allow slow startup)
                if LOGIN_PROMPT_RE.search(output):
                    login_reads += 1
                    if login_reads >= 5:  # Seen for ~2.5 seconds
                        raise AntigravityStatusError(
                            "Antigravity CLI requires login.\n"
                            "Please run 'agy' manually to log in, or use "
                            "'[bold cyan]agm restore <email>[/]' to restore an existing account."
                        )
                else:
                    login_reads = 0

                # 4. Check for First-Time Setup (Onboarding) state (Require stability)
                if ONBOARDING_PROMPT_RE.search(output):
                    onboarding_reads += 1
                    if onboarding_reads >= 5:  # Seen for ~2.5 seconds
                        raise AntigravityStatusError(
                            "Antigravity CLI is in first-time setup mode.\n"
                            "Please complete the onboarding by running 'agy' manually, "
                            "or use '[bold cyan]agm restore <email>[/]' to restore your account."
                        )
                else:
                    onboarding_reads = 0

            if time.time() - start > timeout_seconds:
                raise AntigravityStatusError(
                    "Timed out waiting for fully loaded Antigravity startup."
                )
            time.sleep(0.5)


def wait_for_usage_panel(pane_id: str, *, timeout_seconds: float) -> str:
    start = time.time()
    last_retry = start
    with console.status("[cyan]Fetching usage panel...[/cyan]", spinner="dots"):
        while True:
            output = capture_pane(pane_id)
            if USAGE_HEADER_RE.search(output) and "%" in output:
                return output
            if time.time() - start > timeout_seconds:
                raise AntigravityStatusError("Timed out waiting for /usage output.")
            if time.time() - last_retry > 5:
                run_command(["tmux", "send-keys", "-t", pane_id, "/usage", "Enter"], check=False)
                last_retry = time.time()
            time.sleep(0.5)


def capture_tmux_status_text(
    *,
    session_name: str | None = None,
    agy_command: str = "agy",
    cols: int = 140,
    rows: int = 45,
    startup_timeout_seconds: float = 30.0,
    usage_timeout_seconds: float = 30.0,
) -> str:
    verify_tmux_available()
    if session_name is None:
        session_name = f"agy_status_{os.getpid()}"

    if (
        subprocess.run(["tmux", "has-session", "-t", session_name], capture_output=True).returncode
        == 0
    ):
        run_command(["tmux", "kill-session", "-t", session_name], check=False)

    session = run_command(
        [
            "tmux",
            "new-session",
            "-d",
            "-P",
            "-F",
            "#{pane_id}",
            "-s",
            session_name,
            "-x",
            str(cols),
            "-y",
            str(rows),
            agy_command,
        ]
    )
    pane_id = session.stdout.strip()
    if not pane_id:
        raise AntigravityStatusError("tmux did not return pane id.")

    run_command(["tmux", "set-option", "-t", session_name, "remain-on-exit", "on"])
    try:
        startup_output = wait_for_prompt(pane_id, timeout_seconds=startup_timeout_seconds)
        run_command(["tmux", "send-keys", "-t", pane_id, "/usage", "Enter"])
        usage_output = wait_for_usage_panel(pane_id, timeout_seconds=usage_timeout_seconds)
        return f"\n===== STARTUP =====\n{startup_output}\n===== USAGE =====\n{usage_output}"
    finally:
        run_command(["tmux", "kill-session", "-t", session_name], check=False)


def parse_email_and_plan(text: str) -> tuple[str, str]:
    match = EMAIL_AND_PLAN_RE.search(text)
    if not match:
        raise ValueError("Unable to parse email and plan.")
    email = match.group("email").strip()
    plan = match.group("plan").strip() if match.group("plan") else "Standard"
    return email, plan


def parse_refresh_at(refresh_text: str | None, *, now: datetime) -> datetime | None:
    if not refresh_text:
        return None
    match = REFRESH_RE.search(refresh_text)
    if not match:
        return None
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    return now + timedelta(hours=hours, minutes=minutes)


def is_model_name(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(("│", "└", ">", "-", "█", "░")):
        return False
    if "%" in stripped:
        return False
    if stripped.startswith(
        ("Refreshes in", "Quota available", "esc to cancel", "↑/↓", "? for shortcuts")
    ):
        return False
    return bool(MODEL_NAME_RE.match(stripped))


def parse_model_blocks(text: str, *, now: datetime) -> tuple[ModelQuotaStatus, ...]:
    lines = text.splitlines()
    models: list[ModelQuotaStatus] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not is_model_name(line) or i + 1 >= len(lines):
            i += 1
            continue
        percent_match = QUOTA_PERCENT_RE.search(lines[i + 1])
        if not percent_match:
            i += 1
            continue
        quota_percent = int(percent_match.group(1))
        refresh_text = None
        if i + 2 < len(lines):
            candidate = lines[i + 2].strip()
            if "Refreshes in" in candidate:
                idx = candidate.index("Refreshes in")
                refresh_text = candidate[idx:]
        models.append(
            ModelQuotaStatus(
                model_name=line,
                quota_percent_left=quota_percent,
                refresh_in_text=refresh_text,
                refresh_at=parse_refresh_at(refresh_text, now=now),
                is_available=quota_percent > 0 and refresh_text is None,
            )
        )
        i += 3
    return tuple(models)


def parse_live_status_text(text: str, *, now: datetime | None = None) -> LiveStatus:
    current = now if now is not None else datetime.now().astimezone()
    email, plan = parse_email_and_plan(text)
    return LiveStatus(
        email=email,
        plan=plan,
        is_pro="pro" in plan.lower(),
        captured_at=current,
        models=parse_model_blocks(text, now=current),
    )


def live_status_to_text(status: LiveStatus) -> RenderableType:
    from .ui import Group, Panel, Table, Text

    header = Table.grid(padding=(0, 2))
    header.add_column(style="bold cyan", justify="right")
    header.add_column(style="white")

    header.add_row("Account:", status.email)
    plan_label = "PRO" if status.is_pro else "STANDARD"
    header.add_row("Plan:", f"{status.plan} [dim]({plan_label})[/dim]")
    header.add_row("Captured At:", status.captured_at.strftime("%Y-%m-%d %H:%M:%S %Z"))

    model_table = Table(show_header=True, header_style="bold bright_magenta", box=None)
    model_table.add_column("Model", style="dim white")
    model_table.add_column("Quota", justify="right", width=6)
    model_table.add_column("State", justify="center")
    model_table.add_column("Refresh", justify="right", style="dim")

    for model in status.models:
        quota_text = (
            f"{model.quota_percent_left}%" if model.quota_percent_left is not None else "unknown"
        )
        state_text = "[success]Ready[/]" if model.is_available else "[yellow]Cooldown[/]"

        if model.quota_percent_left is not None:
            if model.quota_percent_left >= 75:
                quota_text = f"[spring_green3]{quota_text}[/]"
            elif model.quota_percent_left >= 50:
                quota_text = f"[yellow3]{quota_text}[/]"
            elif model.quota_percent_left >= 25:
                quota_text = f"[dark_orange]{quota_text}[/]"
            else:
                quota_text = f"[red3]{quota_text}[/]"

        refresh_text = model.refresh_in_text or "available now"
        # Style refresh text as dim to match other dim elements for consistency
        refresh_text = f"[dim]{refresh_text}[/]"

        model_table.add_row(model.model_name, quota_text, state_text, refresh_text)

    content_group = Group(
        header,
        Text(""),
        Text("Models:", style="bold bright_magenta"),
        model_table,
    )

    return Panel(
        content_group,
        title="[bold bright_cyan]Antigravity Live Status[/]",
        border_style="bright_cyan",
        expand=False,
    )
