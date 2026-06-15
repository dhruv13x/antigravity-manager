from __future__ import annotations

import os
import re
import subprocess
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .ui import console

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
USAGE_HEADER_RE = re.compile(r"Models?\s+&\s+Quota|Model Quota", re.IGNORECASE)
QUOTA_EXHAUSTED_RE = re.compile(
    r"(?:quota will reset after|Resets in)\s+(?P<duration>(?:(?P<hours>\d+)h)?\s*(?:(?P<minutes>\d+)m)?\s*(?:(?P<seconds>\d+)s)?)(?:\.|$)",
    re.IGNORECASE,
)
ELIGIBILITY_RE = re.compile(r"Eligibility check failed|verify your account", re.IGNORECASE)
MODEL_NAME_RE = re.compile(r"^(?![│└>])(?=.*[A-Za-z]).+$")
ACTIVE_MODEL_RE = re.compile(
    r"(?P<model>(?:\bGemini\b|\bClaude\b|\bGPT\b)[^·\n\r&?=%]{0,100}?(?:\s*\([^)]+\))?)(?:\s*(?:·|$))",
    re.MULTILINE | re.IGNORECASE,
)
TRUST_PROMPT_RE = re.compile(
    r"Do you trust the contents of this project\?.*requires permission to read, edit, and execute.*Yes, I trust this folder",
    re.IGNORECASE | re.DOTALL,
)


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
    eligibility_reads = 0

    with console.status("[cyan]Waiting for Antigravity startup...[/cyan]", spinner="dots"):
        while True:
            output = capture_pane(pane_id)

            # 1. Handle directory trust prompt (immediate action)
            if TRUST_PROMPT_RE.search(output):
                login_reads = 0
                onboarding_reads = 0
                eligibility_reads = 0
                run_command(["tmux", "send-keys", "-t", pane_id, "Enter"], check=False)
                time.sleep(1)
                continue

            # 2. Check for successful startup (Prompt + Account)
            # This is the primary success condition. If we have a prompt, ignore errors.
            has_prompt = PROMPT_RE.search(output) is not None
            has_account = EMAIL_AND_PLAN_RE.search(output) is not None or "Account:" in output

            if has_prompt and has_account:
                stable_reads += 1
                if stable_reads >= 3:
                    return output
            else:
                stable_reads = 0

                # 3. Check for Eligibility/Verification failure (Require stability)
                if ELIGIBILITY_RE.search(output):
                    eligibility_reads += 1
                    if eligibility_reads >= 5: # Seen for ~2.5 seconds
                        raise AntigravityStatusError(
                            "Antigravity eligibility check failed.\n"
                            "Please run 'agy' manually to verify your account in the browser."
                        )
                else:
                    eligibility_reads = 0

                # 4. Check for Login Required state (Require stability)
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

                # 5. Check for First-Time Setup (Onboarding) state (Require stability)
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
            if USAGE_HEADER_RE.search(output) and ("%" in output or "Loading" in output):
                # If we see "Loading", wait a bit longer but don't hang forever
                if "Loading" in output and time.time() - start < (timeout_seconds * 0.7):
                    time.sleep(1)
                    continue
                return output
            if time.time() - start > timeout_seconds:
                raise AntigravityStatusError("Timed out waiting for /usage output.")
            if time.time() - last_retry > 5:
                run_command(["tmux", "send-keys", "-t", pane_id, "/usage", "Enter"], check=False)
                last_retry = time.time()
            time.sleep(0.5)


def probe_quota_via_message(pane_id: str, *, timeout_seconds: float = 10.0) -> str:
    """Fallback: Send 'hi' to trigger a quota exhausted warning if /usage is stuck."""
    # Ensure we are at the prompt by sending Escape (closes /usage panel)
    run_command(["tmux", "send-keys", "-t", pane_id, "Escape"], check=False)
    time.sleep(0.5)
    run_command(["tmux", "send-keys", "-t", pane_id, "hi", "Enter"], check=False)
    
    start = time.time()
    # First, wait up to 5s specifically for the reset text variations
    # to avoid premature exit due to the prompt that triggered the command.
    while time.time() - start < 5.0:
        output = capture_pane(pane_id)
        if any(k in output.lower() for k in ("quota will reset after", "resets in")):
            time.sleep(0.5)
            return capture_pane(pane_id)
        time.sleep(0.5)
        
    # Then fall back to waiting for ANY prompt or the warning
    while time.time() - start < timeout_seconds:
        output = capture_pane(pane_id)
        if any(k in output.lower() for k in ("quota will reset after", "resets in")) or PROMPT_RE.search(output):
            time.sleep(0.5)
            return capture_pane(pane_id)
        time.sleep(0.5)
    return capture_pane(pane_id)


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
        
        try:
            usage_output = wait_for_usage_panel(pane_id, timeout_seconds=usage_timeout_seconds)
            # If usage output is just "Loading...", try probing as well
            if "Loading" in usage_output and "%" not in usage_output:
                probe_output = probe_quota_via_message(pane_id)
                usage_output = f"{usage_output}\n===== PROBE =====\n{probe_output}"
        except AntigravityStatusError:
            # Fallback to probe if /usage times out
            probe_output = probe_quota_via_message(pane_id)
            usage_output = f"USAGE TIMEOUT\n===== PROBE =====\n{probe_output}"

        return f"\n===== STARTUP =====\n{startup_output}\n===== USAGE =====\n{usage_output}"
    finally:
        run_command(["tmux", "kill-session", "-t", session_name], check=False)


def parse_email_and_plan(text: str) -> tuple[str, str]:
    # Try the new "Account: email" format first (found in /usage)
    account_match = re.search(r"Account:\s*(?P<email>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
    
    # Also look for rich email/plan info (usually found in the banner)
    rich_match = EMAIL_AND_PLAN_RE.search(text)
    
    if account_match:
        email = account_match.group("email").strip()
        # If banner match exists and has same email, use its plan info
        if rich_match and rich_match.group("email") == email and rich_match.group("plan"):
            return email, rich_match.group("plan").strip()
        return email, "Standard"

    if not rich_match:
        raise ValueError("Unable to parse email and plan.")
        
    email = rich_match.group("email").strip()
    plan = rich_match.group("plan").strip() if rich_match.group("plan") else "Standard"
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
    if not stripped or len(stripped) < 2:
        return False
    # Exclude graphics and UI elements
    if stripped.startswith(("│", "└", ">", "-", "█", "░", "▀", "▄", "Account:", "Models within this group:", "Weekly Limit", "Five Hour Limit", "Five-Hour Limit")):
        return False
    # Strict block graphic check
    if any(x in stripped for x in ("▀", "▄", "█", "░", "▒", "▓")):
        return False
    if "%" in stripped:
        return False
    # Exclude noise and URLs
    u_stripped = stripped.upper()
    if any(k in u_stripped for k in ("REFRESHES IN", "QUOTA AVAILABLE", "ESC TO CANCEL", "↑/↓", "? FOR SHORTCUTS", "QUOTA WILL RESET AFTER", "HTTP", "WWW", "FIVE HOUR LIMIT")):
        return False
    if stripped.startswith("===") and stripped.endswith("==="):
        return False
    return bool(MODEL_NAME_RE.match(stripped))


def format_model_group_name(raw_name: str) -> str:
    """Consistently wrap model names in their management groups."""
    # Reject things that look like URLs, noise, or transient limits
    u_raw = raw_name.upper()
    if (
        "://" in raw_name 
        or "HTTP" in u_raw 
        or raw_name.count("/") > 1 
        or "FIVE HOUR LIMIT" in u_raw
        or raw_name.endswith("-")
        or any(x in raw_name for x in ("&", "=", "?", "%", ".COM", ".ORG"))
    ):
        return ""

    clean = re.sub(r"[^A-Za-z0-9\s().,/-]+", "", raw_name).strip()
    clean = " ".join(clean.split())
    
    if not clean or len(clean) < 2:
        return ""

    u_name = clean.upper()

    if "GEMINI" in u_name:
        if "GEMINI MODELS" in u_name:
            return clean
        return f"GEMINI MODELS ({clean})"
    if "CLAUDE" in u_name or "GPT" in u_name:
        if "CLAUDE AND GPT MODELS" in u_name:
            return clean
        return f"CLAUDE AND GPT MODELS ({clean})"
    return clean


def parse_model_blocks(text: str, *, now: datetime) -> tuple[ModelQuotaStatus, ...]:
    # 1. Clean the entire input text to remove block graphics
    clean_text = re.sub(r"[▀▄█░▒▓]+", " ", text)
    lines = clean_text.splitlines()
    models: list[ModelQuotaStatus] = []
    
    # Check for PROBE data first
    probe_refresh_at = None
    probe_refresh_text = None
    if "===== PROBE =====" in clean_text:
        probe_match = QUOTA_EXHAUSTED_RE.search(clean_text)
        if probe_match:
            hours = int(probe_match.group("hours") or 0)
            minutes = int(probe_match.group("minutes") or 0)
            seconds = int(probe_match.group("seconds") or 0)
            probe_refresh_at = now + timedelta(hours=hours, minutes=minutes, seconds=seconds)
            probe_refresh_text = f"Refreshes in {probe_match.group('duration')}"

    i = 0
    quota_percent_re = re.compile(r"(\d+(?:\.\d+)?)%")

    while i < len(lines):
        line = lines[i].strip()
        if not is_model_name(line):
            i += 1
            continue

        model_name = line
        quota_percent = None
        refresh_text = None
        refresh_at = None

        # Look ahead for more info
        j = i + 1
        found_data = False
        while j < len(lines) and j < i + 10:
            next_line = lines[j].strip()

            if "Models within this group:" in next_line:
                sub_models = next_line.split(":", 1)[1].strip()
                if "(" not in model_name:
                    model_name = f"{model_name} ({sub_models})"
                j += 1
                continue

            if is_model_name(next_line):
                break

            percent_match = quota_percent_re.search(next_line)
            if percent_match and quota_percent is None:
                quota_percent = float(percent_match.group(1))
                found_data = True

            if "Refreshes in" in next_line and refresh_text is None:
                idx = next_line.index("Refreshes in")
                refresh_text = next_line[idx:]
                found_data = True

            j += 1
            if quota_percent is not None and refresh_text is not None:
                break

        # Apply PROBE info to likely model if no data found
        if not found_data and probe_refresh_at:
            # Only apply probe data to models that likely match the probe (e.g. Gemini/Claude)
            if any(x in model_name.upper() for x in ("GEMINI", "CLAUDE", "GPT")):
                quota_percent = 0.0
                refresh_at = probe_refresh_at
                refresh_text = probe_refresh_text
                found_data = True

        if found_data and quota_percent is not None:
            name = format_model_group_name(model_name)
            if name:
                models.append(
                    ModelQuotaStatus(
                        model_name=name,
                        quota_percent_left=int(quota_percent),
                        refresh_in_text=refresh_text,
                        refresh_at=refresh_at or parse_refresh_at(refresh_text, now=now),
                        is_available=quota_percent > 0 and refresh_text is None,
                    )
                )
            i = j
        else:
            i += 1
            
    # Fallback/Active Model detection from screen (Banner/Footer)
    matches = list(ACTIVE_MODEL_RE.finditer(clean_text))
    if matches:
        for m in matches:
            raw_name = m.group("model").strip()
            formatted_name = format_model_group_name(raw_name)
            
            if not formatted_name:
                continue
            
            # Smart Deduplication: 
            # If we already have a model in this group with quota information from /usage, 
            # we don't need the fallback.
            group_prefix = formatted_name.split(" (")[0]
            if any(item.model_name.startswith(group_prefix) and item.quota_percent_left is not None for item in models):
                continue
                
            # If not in list, add it
            if not any(item.model_name == formatted_name for item in models):
                if probe_refresh_at:
                    # Confirmed Cooldown via Probe
                    models.append(
                        ModelQuotaStatus(
                            model_name=formatted_name,
                            quota_percent_left=0,
                            refresh_in_text=probe_refresh_text,
                            refresh_at=probe_refresh_at,
                            is_available=False,
                        )
                    )
                else:
                    # Probe didn't trigger a warning -> Empirical proof it's Ready
                    models.append(
                        ModelQuotaStatus(
                            model_name=formatted_name,
                            quota_percent_left=100,
                            refresh_in_text=None,
                            refresh_at=None,
                            is_available=True,
                        )
                    )

    # Final Deduplication by name (preserving order)
    seen_names = set()
    unique_models = []
    for m in models:
        if m.model_name not in seen_names:
            unique_models.append(m)
            seen_names.add(m.model_name)
            
    return tuple(unique_models)


def parse_live_status_text(text: str, *, now: datetime | None = None, existing_status: LiveStatus | None = None) -> LiveStatus:
    current = now if now is not None else datetime.now().astimezone()
    email, plan = parse_email_and_plan(text)
    
    new_models = list(parse_model_blocks(text, now=current))
    
    # If we have existing status data and the new scan was a partial probe (few models),
    # merge the data so we don't lose track of other models.
    if existing_status and existing_status.email == email:
        merged_models = {m.model_name: m for m in existing_status.models}
        
        # Update with new findings
        for m in new_models:
            merged_models[m.model_name] = m
            
        # Re-sort to maintain consistent order (Gemini then Claude/Others)
        sorted_models = sorted(
            merged_models.values(),
            key=lambda x: ("GEMINI" not in x.model_name.upper(), x.model_name)
        )
        new_models = sorted_models

    return LiveStatus(
        email=email,
        plan=plan,
        is_pro="pro" in plan.lower(),
        captured_at=current,
        models=tuple(new_models),
    )


def live_status_to_text(status: LiveStatus) -> RenderableType:
    header = Table.grid(padding=(0, 2))
    header.add_column(style="bold cyan", justify="right")
    header.add_column(style="white")
    header.add_row("Account:", status.email)
    header.add_row("Captured At:", status.captured_at.strftime("%Y-%m-%d %H:%M:%S %Z"))

    model_table = Table(show_header=True, header_style="bold bright_magenta", box=None, padding=(0, 1))
    model_table.add_column("Model")
    model_table.add_column("Quota", justify="right")
    model_table.add_column("State", justify="center")
    model_table.add_column("Refresh", justify="right")

    for model in status.models:
        quota_text = f"{model.quota_percent_left}%" if model.quota_percent_left is not None else "??%"
        state_text = "[bold bright_green]Ready[/]" if model.is_available else "[bold bright_yellow]Cooldown[/]"
        
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
