# antigravity-manager

Account backup, restore, cooldown, and status manager for Antigravity CLI.

## Commands

```bash
uv run agm status
uv run agm backup
uv run agm backup --auth-only
uv run agm backup --decision-model "Gemini 3.5 Flash"
uv run agm restore --email you@example.com
uv run agm restore --from-archive ./backup.tar.gz --full
uv run agm use you@example.com
uv run agm cooldown
uv run agm recommend
uv run agm list-backups
uv run agm doctor
```

Default paths:

- Manager state: `~/.antigravity-manager`
- Backups: `~/.antigravity-manager/backups`
- Antigravity CLI state: `~/.gemini/antigravity-cli`
- Shared Gemini identity files: `~/.gemini`

`agm restore` is auth-only by default. Use `--full` only when you want to replace
the whole Antigravity CLI state directory.

Backups and recommendations use `Gemini 3.5 Flash` as the default decision
model. If Antigravity exposes a reset time for that model, the backup filename is
anchored to that reset time. If the model is available and `/usage` does not show
a reset time, the filename uses an explicit 5-hour estimate and records that
source in metadata.

Before restore/use, `agm` writes an account-named current-state copy under
`~/.antigravity-manager/safety_backups`.
