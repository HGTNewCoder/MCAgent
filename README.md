# Minecraft server management (two agents)

Deterministic orchestrator + DeepSeek **Plugin Manager** and **Verifier** agents. Tools are stubbed under `mock_server/` so you can validate the flow before wiring real RCON/process calls.

See [MEMORY.md](MEMORY.md) for project memory and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for layout rationale.

## Setup

```bash
uv sync
cp .env.example .env   # set DEEPSEEK_API_KEY
```

## Run

```bash
uv run mcserver "Install WorldEdit"          # CLI (recommended)
uv run mcserver-gui                          # GUI
uv run python -m mcserver --gui              # same GUI
uv run python main.py "Install WorldEdit"    # legacy shim (still works)
```

Every run writes output to `logs/YYYY-MM-DD_HH-MM-SS.log`.

## Project layout

```
src/mcserver/          # installable Python package
  agents/              # LLM agents (Plugin Manager, Verifier)
  orchestrator/        # deterministic workflow (no LLM router)
  tools/               # tool schemas + stub implementations
  cli/                 # terminal + GUI entrypoints
tests/                 # unit tests
mock_server/           # local stub data (gitignored)
logs/                  # run logs (gitignored)
```

## Flow

1. Orchestrator receives the request (plain code, not an LLM).
2. Info questions → Plugin Manager answer only.
3. Plugin changes → Plugin Manager → Verifier → success or rollback.
