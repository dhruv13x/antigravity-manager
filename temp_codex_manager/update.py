#!/usr/bin/env python3
# src/gemini_manager/update.py

import os
import shutil
import sys
import json
import urllib.request
from importlib.metadata import version, PackageNotFoundError

from .ui import banner, cprint
from .config import *
from .reset_helpers import run_cmd_safe

PACKAGE_NAME = "gemini-manager"

def get_latest_version():
    """Fetch the latest version of gemini-manager from PyPI."""
    try:
        url = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "Gemini-Manager-CLI"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data["info"]["version"]
    except Exception:
        return "(unknown)"

def do_update():
    banner()
    cprint(NEON_YELLOW, f"[INFO] Updating {PACKAGE_NAME}...")

    python_exe = sys.executable
    
    # Strategy 1: Target current python's pip module
    cmds_to_try = [
        f"{python_exe} -m pip install --upgrade {PACKAGE_NAME}",
    ]
    
    # Strategy 2: Fallback to 'uv' if available (very common in venvs without pip)
    if shutil.which("uv"):
        cmds_to_try.append(f"uv pip install --upgrade {PACKAGE_NAME}")
    
    # Strategy 3: Try generic pip/pip3 on PATH
    if shutil.which("pip3"):
        cmds_to_try.append(f"pip3 install --upgrade {PACKAGE_NAME}")
    elif shutil.which("pip"):
        cmds_to_try.append(f"pip install --upgrade {PACKAGE_NAME}")

    success = False
    last_err = ""
    
    for cmd in cmds_to_try:
        cprint(NEON_YELLOW, f"[INFO] Trying: {cmd} ...")
        rc, out, err = run_cmd_safe(cmd, timeout=300, capture=True, detect_reset_time=False)
        
        if rc == 0:
            cprint(NEON_GREEN, f"\n[OK] Update complete.")
            success = True
            break
        else:
            last_err = err or out or "Unknown error"
            # Handle PEP 668 specifically
            if "externally-managed-environment" in last_err.lower():
                cprint(NEON_RED, "\n[ERROR] Environment is externally managed (PEP 668).")
                choice = input(NEON_CYAN + "Try with --break-system-packages? (y/n): " + RESET).strip().lower()
                if choice == 'y':
                    rc_f, _, err_f = run_cmd_safe(f"{cmd} --break-system-packages", timeout=300, capture=True, detect_reset_time=False)
                    if rc_f == 0:
                        cprint(NEON_GREEN, "\n[OK] Update complete (forced).")
                        success = True
                        break
                    last_err = err_f or "Force update failed"

    if not success:
        cprint(NEON_RED, f"\n[ERROR] Automatic update failed.")
        
        # High-signal hints for common environments
        if os.getenv("CONDA_PREFIX"):
             cprint(NEON_YELLOW, "   [CONDA] Detected Conda. Try: conda update " + PACKAGE_NAME)
        elif os.getenv("POETRY_ACTIVE"):
             cprint(NEON_YELLOW, "   [POETRY] Detected Poetry. Try: poetry add " + PACKAGE_NAME + "@latest")
        elif shutil.which("pipx") and "pipx" in python_exe:
             cprint(NEON_YELLOW, "   [PIPX] Detected pipx. Try: pipx upgrade " + PACKAGE_NAME)
        else:
             cprint(NEON_YELLOW, f"   [TIP] Manual update: {python_exe} -m pip install --upgrade {PACKAGE_NAME}")
        
        cprint(NEON_RED, f"   Last error snippet: {last_err.strip().splitlines()[-1] if last_err else 'None'}")

def do_check_update():
    # We don't call banner() here to avoid double-printing if called from main help
    # But do_check_update is called from a specific flag, so banner is fine.
    banner()
    cprint(NEON_YELLOW, "[INFO] Checking Gemini CLI version...")

    # Get installed version directly
    try:
        installed = version(PACKAGE_NAME)
    except PackageNotFoundError:
        installed = "23.0.0" # Fallback to hardcoded version

    cprint(NEON_CYAN, f"[INFO] Installed version: {NEON_GREEN}{installed}")

    # Get latest version from PyPI
    latest = get_latest_version()
    cprint(NEON_CYAN, f"[INFO] Latest version:    {NEON_GREEN}{latest}")

    if latest != "(unknown)" and installed == latest:
        cprint(NEON_GREEN, "\n[OK] You already have the latest version!")
        return

    if latest == "(unknown)":
        cprint(NEON_YELLOW, "\n[WARN] Could not determine the latest version online.")
        return

    cprint(NEON_MAGENTA, "\n⚡ Update available!")
    try:
        choice = input(NEON_YELLOW + "Do you want to update? (y/n): " + RESET).strip().lower()
    except EOFError:
        choice = "n"
        
    if choice == "y":
        do_update()
    else:
        cprint(NEON_CYAN, "Update cancelled.\n")

def do_check_update_silent():
    """Silent check for internal use."""
    try:
        installed = version(PACKAGE_NAME)
    except PackageNotFoundError:
        installed = "23.0.0"
    
    latest = get_latest_version()
    if latest != "(unknown)" and installed != latest:
        return True, installed, latest
    return False, installed, latest
