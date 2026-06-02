# 🌌 Antigravity Manager

A stateful command-line tool for backup, restore, cooldown tracking, account rotation, cloud sync, and safety recovery for the Antigravity CLI.

It is designed for operators who manage multiple Antigravity accounts across one or more machines and need a clean, reliable, and low-friction workflow.

## What it gives you

- Live status capture from the Antigravity CLI using tmux
- Cooldown-aware account orchestration with account readiness tracking
- Relative-time dashboards that are easier to scan than raw timestamps
- Cloud-aware state reconciliation for local + remote backup inventories
- Safety-first restore and purge flows with automatic recovery points
- Rich terminal output that is readable in a real shell, not just in logs
- Machine-readable JSON output for scripting and automation

## Key behavior

### `agm status`

Captures the current state of the Antigravity CLI and shows:

- active account
- plan
- capture time
- model quota status
- cooldown / ready state
- refresh timing

The status command now handles real-world CLI conditions more gracefully, including:

- login-required states
- first-time onboarding states
- slow startup windows
- clearer failure guidance instead of generic timeout-style behavior

### `agm cooldown`

Shows a consolidated account readiness table with:

- grouped model usage
- deduplicated cooldown rows
- current account state
- next reset timing
- relative Last Checked values like `2m ago`, `1h ago`, `1d ago`

This makes the dashboard much faster to read than absolute timestamps.

### `agm backup`

Creates a backup archive of the Antigravity CLI state and writes metadata that can be used later for:

- restore
- cooldown evaluation
- recommendation
- cloud sync

Backups are timestamped and can be anchored to the decision model used for availability calculations.

### `agm recommend`

Evaluates which account is ready next and helps you choose the best available one.

### `agm recommend --use`

Switches to the recommended account immediately.

### `agm restore <email>` / `agm use <email>`

Restores an account from an existing backup. `use` is a specialized auth-only restore for quick account switching.

### `agm purge -y`

Factory-resets the Antigravity home after creating a safety backup first.

### `agm sync push` / `agm sync pull`

Synchronizes local backup state with cloud storage.

### `agm prune`

Cleans temporary runtime files, logs, and caches within the active Antigravity CLI state without destroying active profile state.

### `agm list-backups`

Lists known backups locally.

### `agm list-backups --cloud`

Shows the cloud inventory only, without mixing local artifacts into the view.

## Quick start

### Prerequisites

- Python 3.12 or newer
- tmux for live status capture
- uv recommended, or pip
- Antigravity CLI installed at `~/.gemini/antigravity-cli` by default

### Install

```bash
git clone https://github.com/dhruv13x/antigravity-manager.git
cd antigravity-manager
uv pip install .
```

Or with pip:

```bash
pip install .
```

### Run

```bash
agm
```

The default command opens the cooldown dashboard.

## Typical workflow

```bash
# Check the live state of the current Antigravity session
agm status

# Save the current account state
agm backup

# Inspect all known accounts and their readiness
agm cooldown

# View local backup inventory
agm list-backups

# View only cloud-backed inventory
agm list-backups --cloud

# Sync local state to cloud
agm sync push

# Pull cloud state back locally
agm sync pull

# Rotate to the best available account
agm recommend --use

# Recover from a bad reset or login loss
agm restore someone@example.com
```

## Features

### Smart orchestration

- **Deduplicated cooldown dashboard**: groups models that share the same quota/reset timing so the table stays compact.
- **One-command switching**: rotate to a ready account using `agm recommend --use`.
- **Merged local + cloud reasoning**: uses the latest known state across local and remote metadata when evaluating readiness.

### Safety and reliability

- **CLI state detection**: distinguishes prompt, login, and onboarding states.
- **Grace period for startup**: avoids false failures when the CLI starts slowly.
- **Automatic safety backups**: destructive operations create recovery points before modifying state.
- **Preserved identity state**: cleanup commands avoid removing authentication and persistent manager data unless explicitly intended.

### Maintenance and lifecycle control

- **Targeted pruning**: remove redundant backup artifacts while preserving required state.
- **Cloud isolation mode**: inspect remote backup data without contaminating local views.
- **Cloud sync support**: keep backup archives and metadata mirrored across machines.

### Terminal UX

- **Rich output**: tables, semantic colors, and readable layout.
- **Relative freshness labels**: Last Checked is shown as `2m ago`, `3h ago`, etc.
- **Script-friendly output**: major commands support `--json`.

## Command reference

### Global shortcuts

| Flag | Description |
|------|-------------|
| `-c`, `--cooldown` | Shortcut for cooldown |
| `-s`, `--status` | Shortcut for status |
| `--json` | Output structured JSON instead of Rich tables |

### Backup and restore

| Command / Flag | Description |
|----------------|-------------|
| `agm backup` | Create a backup archive and metadata |
| `--auth-only` | Backup only identity/auth files |
| `--full` | Restore the full Antigravity state directory |
| `agm restore <email>` | Restore an account from backup |
| `agm purge -y` | Factory reset after creating a safety backup |

### Status and orchestration

| Command / Flag | Description |
|----------------|-------------|
| `agm status` | Capture and display live CLI state |
| `agm cooldown` | Show readiness and cooldown dashboard |
| `agm recommend` | Evaluate the best account to use next |
| `agm recommend --use` | Switch immediately to the recommended account |
| `--decision-model` | Anchor timestamps and decisions to a specific model |

### Backup inventory and cloud sync

| Command / Flag | Description |
|----------------|-------------|
| `agm list-backups` | List local backups |
| `agm list-backups --cloud` | List cloud-only backups |
| `agm sync push` | Push local state to cloud storage |
| `agm sync pull` | Pull cloud state into the local workspace |
| `agm prune` | Clean local runtime state |
| `--cloud` | Operate on remote state where supported |

## Configuration

### Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AGM_HOME` | Base directory for manager state | `~/.antigravity-manager` |
| `GEMINI_HOME` | Base directory for Gemini tooling | `~/.gemini` |
| `ANTIGRAVITY_HOME` | Location of the Antigravity CLI | `$GEMINI_HOME/antigravity-cli` |
| `ANTIGRAVITY_SESSION_DIR` | Session symlink/config location | `~/.antigravitycli` |
| `GEMINI_CONFIG_DIR` | Gemini project/session config directory | `$GEMINI_HOME/config` |

Cloud storage credentials and provider settings are resolved from your environment and the configured sync backend.

## How it works

1. **State capture**: `agm status` opens a headless tmux session, inspects the CLI state, and extracts readiness/cooldown information.
2. **Archival**: `agm backup` bundles the Antigravity CLI state into a timestamped archive and records metadata for later evaluation.
3. **Orchestration**: `agm cooldown` and `agm recommend` evaluate local and cloud metadata to determine which accounts are ready.
4. **Restoration**: `agm restore` or `agm use` recreates a working account state from a backup, with safety recovery points automatically generated before any destructive operations.
5. **Lifecycle cleanup**: `agm prune` and `agm sync` keep the workspace and cloud inventory consistent without losing important identity state.

## Output examples

### Live status

```text
Captured At: 2026-05-26 18:32:16 IST

Models:
 Gemini 3.5 Flash (Medium)     60% Cooldown  Refreshes in 167h 32m
 Claude Sonnet 4.6 (Thinking)   0% Cooldown  Refreshes in 167h 26m
```

### Cooldown dashboard (Smart Grouping)

```text
Account                      Status     Usage                     Last Checked
user1@example.com            READY      G3.5F High   100% Ready         1h ago
user2@example.com            COOLDOWN   G3.5F High     0% 5d2h46m       1d ago
                                        Son4.6 Think  60% Ready
active@example.com           ACTIVE     G3.5F High    60% 6d23h32m      2m ago
                                        Son4.6 Think   0% 6d23h27m
```

### Sync behavior

```
Skipping existing backup, already present in cloud.
Uploading new archive...
Successfully uploaded status and metadata files.
```

## Troubleshooting

| Error message | What it usually means |
|---------------|----------------------|
| `Antigravity CLI requires login.` | The CLI is at a login screen or session is not authenticated |
| `Antigravity CLI is in first-time setup mode.` | Finish onboarding in `agy` before using `agm status` |
| `Use either --auth-only or --full, not both.` | Those restore modes are mutually exclusive |
| `No account status found.` | Run `agm backup` or `agm status` first |
| `tmux: command not found` | Install tmux so live status capture can work |

## Developer setup

```bash
uv pip install -e ".[dev]"
uv run pytest
uv run ruff check
uv run ruff format .
uv run mypy src
```

## Repository layout

```
src/antigravity_manager/
├── cli.py
├── config.py
├── ui.py
├── utils.py
├── credentials.py
├── registry.py
├── status.py
├── backup.py
├── restore.py
├── cooldown.py
├── list_backups.py
├── prune.py
├── sync.py
└── ...
```

## Roadmap

- Add more backup encryption options
- Reduce dependency on terminal scraping where possible
- Add notifications for account readiness changes
- Support continuous daemon-style monitoring
- Expand cloud-provider abstractions

## Contributing

Contributions are welcome. Please keep changes focused, documented, and covered by tests where appropriate.

## License

MIT
