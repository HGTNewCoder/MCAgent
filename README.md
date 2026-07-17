# Minecraft server management (two agents)

Deterministic orchestrator + DeepSeek **Plugin Manager** and **Verifier** agents. Tools are stubbed under `mock_server/` so you can validate the flow before wiring real RCON/process calls.

See [MEMORY.md](MEMORY.md) for project memory and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for layout rationale.

## Setup

```bash
uv sync
cp .env.example .env   # set DEEPSEEK_API_KEY
```

For the web UI:

```bash
cd web && npm install
```

## Run

```bash
uv run mcserver "Install WorldEdit"          # CLI
uv run mcserver-gui                          # Tkinter GUI (legacy demo)
uv run python -m mcserver --gui              # same GUI
uv run python main.py "Install WorldEdit"    # legacy shim (still works)
```

### Web UI (demo product surface)

Terminal 1 — API:

```bash
uv run mcserver-api                          # FastAPI on http://127.0.0.1:8000
```

Terminal 2 — Vite:

```bash
cd web && npm run dev                        # http://127.0.0.1:5173 (proxies /api)
```

OpenAPI docs: http://127.0.0.1:8000/docs

Every orchestrator run writes output to `logs/YYYY-MM-DD_HH-MM-SS.log`.

Process control (`start_server` / `stop_server` / `restart_server`) drives the real Java process when `server/server.jar` exists (`MC_PROCESS_MODE=auto`).

## Project layout

```
src/mcserver/          # installable Python package
  agents/              # LLM agents (Plugin Manager, Verifier)
  orchestrator/        # deterministic workflow (no LLM router)
  tools/               # tool schemas + stub / process implementations
  api/                 # FastAPI bridge for the web UI
  cli/                 # terminal + Tkinter entrypoints
web/                   # React + Vite + TypeScript + Tailwind demo UI
tests/                 # unit tests
mock_server/           # local stub data (gitignored)
logs/                  # run logs (gitignored)
```

## Flow

1. Orchestrator receives the request (plain code, not an LLM).
2. Info questions → Plugin Manager answer only.
3. Plugin changes → Plugin Manager → Verifier → success or rollback.
