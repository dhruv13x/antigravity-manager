# 🌌 Antigravity Manager

**The definitive account backup, restore, cooldown, and orchestration manager for Antigravity CLI.**

![Build Status](https://img.shields.io/github/actions/workflow/status/dhruv13x/antigravity-manager/main.yml?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)
![Python Version](https://img.shields.io/badge/python-%3E%3D3.12-blue?style=flat-square)
![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![Maintenance Status](https://img.shields.io/badge/maintenance-active-success.svg?style=flat-square)

---

## ⚡ Quick Start (The "5-Minute Rule")

### Prerequisites
- Python >= 3.12
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Installed Antigravity CLI at `~/.gemini/antigravity-cli` (default)

### Install
```bash
git clone https://github.com/dhruv13x/antigravity-manager.git
cd antigravity-manager
uv pip install .
```

### Run
```bash
# Display the default cooldown dashboard
agm
```

### Demo
*(![CLI Demo](assets/demo.gif))*

```bash
# 1. Back up your current active account
agm backup --auth-only --decision-model "Gemini 3.5 Flash"

# 2. Get a recommendation for which account to use next
agm recommend

# 3. Immediately switch to the recommended account
agm recommend --use

# 4. Check status and cooldowns
agm status
agm cooldown
```

---

## ✨ Features (The "Why")

### Core Orchestration
- **Smart Cooldown Tracking**: Evaluates the cooldown state of backups against your selected decision model (e.g., `Gemini 3.5 Flash`).
- **One-Command Swapping**: Instantly rotate to the best available account via `agm recommend --use`.
- **Safety First**: Automatically takes a safety backup before overwriting your active Antigravity CLI state.
- **S3 Cloud Sync**: Safely sync your backup archive to any S3-compatible cloud storage (`agm sync`).

### Performance & UI
- **Rich Terminal UI**: Visually premium outputs leveraging tables, semantic colors, and structured layouts for clear insights.
- **Lightning Fast**: Built on Python 3.12 and rigorously typed for fast execution.
- **Machine-Readable**: Every major command supports `--json` for seamless script integration.

### Security
- **Auth-Only Backups**: Limit backups to only vital identity and settings files with `--auth-only`.
- **GPG Encryption**: Encrypt your critical credentials on disk using `--encrypt`.

---

## 🛠️ Configuration (The "How")

### Environment Variables

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `AGM_HOME` | Base directory for manager state. | `~/.antigravity-manager` | No |
| `GEMINI_HOME` | Base directory for Gemini tools. | `~/.gemini` | No |
| `ANTIGRAVITY_HOME` | Location of the Antigravity CLI. | `$GEMINI_HOME/antigravity-cli` | No |
| `ANTIGRAVITY_SESSION_DIR` | Location of session symlink/config. | `~/.antigravitycli` | No |
| `GEMINI_CONFIG_DIR` | Gemini project/session config dir. | `$GEMINI_HOME/config` | No |

### Key CLI Arguments

| Flag | Command | Description |
| :--- | :--- | :--- |
| `-c`, `--cooldown` | `(Global)` | Shortcut for 'cooldown' command (default). |
| `-s`, `--status` | `(Global)` | Shortcut for 'status' command. |
| `--auth-only` | `backup`, `restore` | Archive/restore only identity and auth files. |
| `--full` | `restore` | Restore the full Antigravity state directory. |
| `--decision-model` | `backup`, `recommend` | The LLM model to anchor timestamps and recommendations. |
| `--dry-run` | `(Most)` | Simulate the command and show what would happen. |
| `--json` | `(Most)` | Output results as structured JSON instead of Rich UI. |

---

## 🏗️ Architecture

### Directory Tree

```text
src/antigravity_manager/
├── __init__.py       # Package definition
├── cli.py            # Main CLI entrypoint (argparse)
├── config.py         # Environment variables & constants
├── ui.py             # Rich console output formatting
├── utils.py          # Path expansions & file helpers
├── credentials.py    # S3 Sync credential resolution
├── registry.py       # Metadata saving & tracking
├── status.py         # tmux capture & /usage parsing
├── backup.py         # Backup creation logic
├── restore.py        # Safety backups & restoration
├── cooldown.py       # Cooldown evaluation logic
├── list_backups.py   # Inventory management
├── prune.py          # State cleanup
├── sync.py           # S3 push/pull integration
└── ...
```

### Flow

1. **State Capture**: `agm status` drops into a headless tmux session, runs `/usage` in Antigravity, and extracts cooldown reset timers.
2. **Archival**: `agm backup` bundles `~/.gemini/antigravity-cli` auth files into a `.tar.gz` and stamps it with the extracted cooldown timer in its metadata.
3. **Orchestration**: `agm cooldown` & `agm recommend` scan the local backup directory metadata, evaluating remaining seconds until an account is "Ready".
4. **Restoration**: `agm use <account>` generates a safety backup of the current state, purges the old state, and unpacks the requested `.tar.gz`.

---

## 🐞 Troubleshooting

### Common Issues

| Error Message | Solution |
| :--- | :--- |
| `Use either --auth-only or --full, not both.` | These flags are mutually exclusive. Choose whether to replace the whole dir (`--full`) or just the identity files (`--auth-only`). |
| `Use either --use or --restore, not both.` | `agm recommend` can only trigger one post-action. `--use` is an auth-only restore; `--restore` is a full restore. |
| `No account status or backup metadata found.` | You must run `agm backup` or `agm status` at least once before requesting a recommendation. |
| `tmux: command not found` | `agm status` relies on `tmux` to capture live CLI output. Ensure tmux is installed via your package manager. |

### Debug Mode

To integrate with scripts or see raw data structures without UI formatting, append the `--json` flag to commands.

```bash
agm doctor --json
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Developer Setup

This project uses `uv` for dependency management and requires Python 3.12+.

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests with coverage
uv run pytest

# Run linters and formatters
uv run ruff check
uv run black .
uv run mypy src
```

---

## 🗺️ Roadmap

- [ ] Support for multiple backup encryption keys.
- [ ] Direct API integration to bypass `tmux` status scraping.
- [ ] Webhook notifications on account readiness.
- [ ] Automated daemon mode for continuous account rotation.
