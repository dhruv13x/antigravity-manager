from __future__ import annotations

import os
import re
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    from .ui import console
except ImportError:
    from rich.console import Console

    console = Console()


EMAIL_AND_PLAN_RE = re.compile(
    r"(?P<email>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\s*\((?P<plan>[^)]+)\)"
)

QUOTA_PERCENT_RE = re.compile(r"(\d+)%")

REFRESH_RE = re.compile(
    r"Refreshes in\s+(?:(?P<hours>\d+)h)?\s*(?:(?P<minutes>\d+)m)?",
    re.IGNORECASE,
)

PROMPT_RE = re.compile(r"[›>]")

USAGE_HEADER_RE = re.compile(
    r"Model Quota",
    re.IGNORECASE,
)

MODEL_NAME_RE = re.compile(
    r"^(?![│└>])(?=.*\()(?=.*\))(?=.*[A-Za-z]).+$"
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


def run_command(
    args: Sequence[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        text=True,
        capture_output=True,
    )

    if check and result.returncode != 0:
        raise AntigravityStatusError(
            f"Command failed: {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return result


def verify_tmux_available() -> None:
    try:
        subprocess.run(
            ["tmux", "-V"],
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise AntigravityStatusError(
            "tmux is required for Antigravity status capture."
        ) from None


def capture_pane(pane_id: str) -> str:
    return run_command(
        ["tmux", "capture-pane", "-t", pane_id, "-p"]
    ).stdout

def wait_for_prompt(
    pane_id: str,
    *,
    timeout_seconds: float,
) -> str:
    start = time.time()

    stable_reads = 0

    with console.status(
        "[cyan]Waiting for Antigravity startup...[/cyan]",
        spinner="dots",
    ):
        while True:
            output = capture_pane(pane_id)

            has_prompt = PROMPT_RE.search(output) is not None
            has_account = EMAIL_AND_PLAN_RE.search(output) is not None

            if has_prompt and has_account:
                stable_reads += 1
            else:
                stable_reads = 0

            # Require multiple stable reads
            # so we don't capture during partial rendering
            if stable_reads >= 3:
                return output

            if time.time() - start > timeout_seconds:
                raise AntigravityStatusError(
                    "Timed out waiting for fully loaded Antigravity startup."
                )

            time.sleep(0.5)



def wait_for_usage_panel(
    pane_id: str,
    *,
    timeout_seconds: float,
) -> str:
    start = time.time()
    last_retry = start

    with console.status(
        "[cyan]Fetching usage panel...[/cyan]",
        spinner="dots",
    ):
        while True:
            output = capture_pane(pane_id)

            if (
                USAGE_HEADER_RE.search(output)
                and "%" in output
            ):
                return output

            if time.time() - start > timeout_seconds:
                raise AntigravityStatusError(
                    "Timed out waiting for /usage output."
                )

            if time.time() - last_retry > 5:
                run_command(
                    [
                        "tmux",
                        "send-keys",
                        "-t",
                        pane_id,
                        "/usage",
                        "Enter",
                    ],
                    check=False,
                )

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

    has_session = (
        subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
        ).returncode
        == 0
    )

    if has_session:
        run_command(
            ["tmux", "kill-session", "-t", session_name],
            check=False,
        )

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
        raise AntigravityStatusError(
            "tmux did not return pane id."
        )

    run_command(
        [
            "tmux",
            "set-option",
            "-t",
            session_name,
            "remain-on-exit",
            "on",
        ]
    )

    try:
        startup_output = wait_for_prompt(
            pane_id,
            timeout_seconds=startup_timeout_seconds,
        )

        run_command(
            [
                "tmux",
                "send-keys",
                "-t",
                pane_id,
                "/usage",
                "Enter",
            ]
        )

        usage_output = wait_for_usage_panel(
            pane_id,
            timeout_seconds=usage_timeout_seconds,
        )

        return (
            "\n===== STARTUP =====\n"
            + startup_output
            + "\n===== USAGE =====\n"
            + usage_output
        )

    finally:
        run_command(
            ["tmux", "kill-session", "-t", session_name],
            check=False,
        )


def parse_email_and_plan(
    text: str,
) -> tuple[str, str]:
    match = EMAIL_AND_PLAN_RE.search(text)

    if not match:
        raise ValueError(
            "Unable to parse email and plan."
        )

    return (
        match.group("email").strip(),
        match.group("plan").strip(),
    )


def parse_refresh_at(
    refresh_text: str | None,
    *,
    now: datetime,
) -> datetime | None:
    if not refresh_text:
        return None

    match = REFRESH_RE.search(refresh_text)

    if not match:
        return None

    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)

    return now + timedelta(
        hours=hours,
        minutes=minutes,
    )


def is_model_name(line: str) -> bool:
    stripped = line.strip()

    if not stripped:
        return False

    if stripped.startswith(("│", "└", ">", "-", "█", "░")):
        return False

    if "%" in stripped:
        return False

    if stripped.startswith("Refreshes in"):
        return False

    if stripped.startswith("Quota available"):
        return False

    if stripped.startswith("esc to cancel"):
        return False

    if stripped.startswith("↑/↓"):
        return False

    if stripped.startswith("? for shortcuts"):
        return False

    return bool(MODEL_NAME_RE.match(stripped))


def parse_model_blocks(
    text: str,
    *,
    now: datetime,
) -> tuple[ModelQuotaStatus, ...]:
    lines = text.splitlines()

    models: list[ModelQuotaStatus] = []

    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not is_model_name(line):
            i += 1
            continue

        if i + 1 >= len(lines):
            i += 1
            continue

        quota_line = lines[i + 1]

        percent_match = QUOTA_PERCENT_RE.search(
            quota_line
        )

        if not percent_match:
            i += 1
            continue

        quota_percent = int(
            percent_match.group(1)
        )

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
                refresh_at=parse_refresh_at(
                    refresh_text,
                    now=now,
                ),
                is_available=quota_percent > 0 and refresh_text is None,
            )
        )

        i += 3

    return tuple(models)


def parse_live_status_text(
    text: str,
    *,
    now: datetime | None = None,
) -> LiveStatus:
    current = (
        now
        if now is not None
        else datetime.now().astimezone()
    )

    email, plan = parse_email_and_plan(text)

    models = parse_model_blocks(
        text,
        now=current,
    )

    return LiveStatus(
        email=email,
        plan=plan,
        is_pro="pro" in plan.lower(),
        captured_at=current,
        models=models,
    )


def live_status_to_text(
    status: LiveStatus,
) -> str:
    lines = [
        f"email: {status.email}",
        f"plan: {status.plan}",
        f"is_pro: {status.is_pro}",
        f"captured_at: {status.captured_at.isoformat()}",
        "",
        "models:",
    ]

    for model in status.models:
        lines.extend(
            [
                f"  - model_name: {model.model_name}",
                (
                    "    quota_percent_left: "
                    f"{model.quota_percent_left}"
                ),
                (
                    "    available: "
                    f"{model.is_available}"
                ),
                (
                    "    refresh_in: "
                    f"{model.refresh_in_text or 'Quota available'}"
                ),
                (
                    "    refresh_at: "
                    f"{model.refresh_at.isoformat() if model.refresh_at else 'available_now'}"
                ),
            ]
        )

    return "\n".join(lines)


if __name__ == "__main__":
    try:
        raw_text = capture_tmux_status_text()

        status = parse_live_status_text(raw_text)

        console.print()
        console.print(
            "[bold green]Antigravity Status[/bold green]"
        )
        console.print()

        console.print(
            live_status_to_text(status)
        )

    except Exception as exc:
        console.print(
            f"[bold red]Error:[/bold red] {exc}"
        )
        raise
