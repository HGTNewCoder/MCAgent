# Minecraft server management (two agents)

Deterministic orchestrator + DeepSeek **Plugin Manager** and **Verifier** agents. Tools are stubbed under `mock_server/` so you can validate the flow before wiring real RCON/process calls.

See [MEMORY.md](MEMORY.md) for architecture memory and next steps.

## Setup

```bash
uv sync
cp .env.example .env   # set DEEPSEEK_API_KEY
```

## Run

```bash
uv run python gui.py                                            # minimal GUI
uv run python main.py --gui                                     # same GUI via CLI flag
uv run python main.py "Install WorldEdit"                       # terminal
uv run python main.py --force-unhealthy "Install LuckPerms"     # stub: force rollback path
uv run python main.py --json "Configure LuckPerms storage=yaml"
```

Every run writes agent/orchestrator output to `logs/YYYY-MM-DD_HH-MM-SS.log`.

## Flow

1. Orchestrator receives the request (no LLM routing).
2. Plugin Manager searches/installs/configures (allowlist only), backups first, returns `change_record`.
3. Verifier checks process, logs, plugin load, smoke test → `{healthy, reason}`.
4. Healthy → success; unhealthy → rollback from `backup_path`, restart, failure report.
