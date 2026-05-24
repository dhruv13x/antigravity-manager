import re

with open('src/antigravity_manager/cli.py', 'r') as f:
    content = f.read()

# Refactor handle_recommend output
recommend_impl = '''
def handle_recommend(args: argparse.Namespace) -> None:
    from .ui import Panel, Table

    entries = list_backups(Path(args.backup_dir).expanduser(), latest_per_email=True)
    statuses = evaluate_entries(entries, decision_model=args.decision_model)
    if not statuses:
        raise FileNotFoundError("No account status or backup metadata found.")
    selected = statuses[0]
    if args.json:
        console.print(json.dumps(asdict(selected), indent=2, default=str), markup=False)
    else:
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan", justify="right")
        table.add_column(style="white")

        table.add_row("Email:", str(selected.email))
        table.add_row("Status:", str(selected.status))
        table.add_row("Decision Model:", str(selected.decision_model))

        avail_status = selected.decision_model_status.is_available if selected.decision_model_status else 'unknown'
        table.add_row("Model Available:", str(avail_status))
        table.add_row("Available In:", format_remaining(selected.remaining_seconds))
        table.add_row("All Models:", f"{selected.available_models}/{selected.total_models}")
        table.add_row("Source:", str(selected.source))

        console.print(Panel(
            table,
            title="[success]Recommended Account[/]",
            border_style="success",
            expand=False
        ))

    if args.use:
        args.email = selected.email
        args.full = False
        args.force = False
        args.from_archive = None
        handle_use(args)
'''
content = re.sub(r'def handle_recommend\(.*?\n\).*?handle_use\(args\)', recommend_impl.strip(), content, flags=re.DOTALL)

# Refactor handle_sync to use status spinners
sync_impl = '''
def handle_sync(args: argparse.Namespace) -> None:
    backup_dir = Path(args.backup_dir).expanduser()
    access_key, secret_key, bucket_name, endpoint_url = resolve_credentials(args)

    if args.direction == "push":
        with console.status(f"[bold cyan]Pushing backups to {bucket_name}...[/]", spinner="dots"):
            push_backup(
                backup_dir=backup_dir,
                bucket_name=bucket_name,
                endpoint_url=endpoint_url,
                access_key=access_key,
                secret_key=secret_key,
                dry_run=args.dry_run,
            )
    elif args.direction == "pull":
        with console.status(f"[bold cyan]Pulling backups from {bucket_name}...[/]", spinner="dots"):
            pull_backup(
                backup_dir=backup_dir,
                bucket_name=bucket_name,
                endpoint_url=endpoint_url,
                access_key=access_key,
                secret_key=secret_key,
                dry_run=args.dry_run,
            )
'''
content = re.sub(r'def handle_sync\(.*?\n\).*?dry_run=args\.dry_run,\n        \)', sync_impl.strip(), content, flags=re.DOTALL)

with open('src/antigravity_manager/cli.py', 'w') as f:
    f.write(content)
