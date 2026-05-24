import sys
import questionary
from argparse import Namespace
from antigravity_manager.ui import banner, print_info, print_error

def _build_fake_args(command: str, **kwargs) -> Namespace:
    args = Namespace(command=command, json=False)
    for k, v in kwargs.items():
        setattr(args, k, v)
    return args

def _handle_cooldown_menu():
    from antigravity_manager.config import DEFAULT_BACKUP_DIR, DEFAULT_DECISION_MODEL, DEFAULT_COOLDOWN_DISPLAY_LIMIT
    from antigravity_manager.cli import handle_cooldown
    args = _build_fake_args(
        "cooldown",
        backup_dir=str(DEFAULT_BACKUP_DIR),
        limit=DEFAULT_COOLDOWN_DISPLAY_LIMIT,
        decision_model=DEFAULT_DECISION_MODEL
    )
    handle_cooldown(args)

def _handle_list_backups_menu():
    from antigravity_manager.config import DEFAULT_BACKUP_DIR
    from antigravity_manager.cli import handle_list_backups
    args = _build_fake_args("list-backups", backup_dir=str(DEFAULT_BACKUP_DIR), email=None, latest_per_email=False)
    handle_list_backups(args)

def _handle_backup_menu():
    from antigravity_manager.config import DEFAULT_BACKUP_DIR, DEFAULT_DECISION_MODEL, ANTIGRAVITY_HOME, GEMINI_HOME
    from antigravity_manager.cli import handle_backup

    auth_only = questionary.confirm("Auth-only backup?").ask()
    if auth_only is None: return

    args = _build_fake_args(
        "backup",
        backup_dir=str(DEFAULT_BACKUP_DIR),
        source_dir=str(ANTIGRAVITY_HOME),
        gemini_home=str(GEMINI_HOME),
        decision_model=DEFAULT_DECISION_MODEL,
        auth_only=auth_only,
        dry_run=False,
        force=False,
        encrypt=False,
        include_bin=False,
        include_logs=False,
        without_status_check=False,
        status_file=None,
        tmux_session_name=None,
        agy_command="agy",
        tmux_cols=140,
        tmux_rows=45,
        startup_timeout_seconds=30.0,
        usage_timeout_seconds=30.0
    )
    try:
        handle_backup(args)
    except Exception as e:
        print_error(str(e))

def _handle_maintenance_menu():
    choice = questionary.select(
        "Maintenance & Doctor",
        choices=[
            "Run System Diagnostic (doctor)",
            "Prune runtime state",
            "Back to Main Menu"
        ]
    ).ask()

    if not choice or choice == "Back to Main Menu":
        return

    if choice.startswith("Run System Diagnostic"):
        from antigravity_manager.config import DEFAULT_BACKUP_DIR, ANTIGRAVITY_HOME, GEMINI_HOME
        from antigravity_manager.cli import handle_doctor
        args = _build_fake_args(
            "doctor",
            backup_dir=str(DEFAULT_BACKUP_DIR),
            source_dir=str(ANTIGRAVITY_HOME),
            gemini_home=str(GEMINI_HOME),
            access_key=None,
            secret_key=None,
            bucket_name=None,
            endpoint_url=None
        )
        try:
            handle_doctor(args)
        except Exception as e:
            print_error(str(e))
    elif choice.startswith("Prune runtime state"):
        from antigravity_manager.config import ANTIGRAVITY_HOME
        from antigravity_manager.cli import handle_prune
        args = _build_fake_args("prune", source_dir=str(ANTIGRAVITY_HOME), dry_run=False)
        try:
            handle_prune(args)
        except Exception as e:
            print_error(str(e))


def interactive_menu(args: Namespace) -> None:
    banner()
    while True:
        choice = questionary.select(
            "Antigravity Manager Main Menu",
            choices=[
                "View Cooldown Status",
                "List Backups",
                "Create Backup",
                "Maintenance & Diagnostics",
                "Exit"
            ]
        ).ask()

        if not choice or choice == "Exit":
            print_info("Exiting Antigravity Manager.")
            sys.exit(0)

        if choice == "View Cooldown Status":
            _handle_cooldown_menu()
        elif choice == "List Backups":
            _handle_list_backups_menu()
        elif choice == "Create Backup":
            _handle_backup_menu()
        elif choice == "Maintenance & Diagnostics":
            _handle_maintenance_menu()
        print("") # Spacing after command execution
