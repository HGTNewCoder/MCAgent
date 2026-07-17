# Project memory — two-agent Minecraft server management

Use this file (and `.cursor/rules/minecraft-two-agent.mdc`) to resume work in a new chat.

## Goal

Build a **two-agent** Minecraft server management system with a **deterministic orchestrator** (plain Python, **no LLM router**).

```
User request
  → Orchestrator (code)
  → info question? → Plugin Manager answer → user (skip Verifier)
  → else → Plugin Manager → change_record → Verifier → healthy? success / rollback
```

## Layout (src package: `mcserver`)

```
src/mcserver/
  agents/           # Plugin Manager + Verifier (DeepSeek tool-calling)
  orchestrator/     # service.py (flow), routing.py (info mode), report.py
  tools/
    registry/       # schemas + dispatch maps
    stub/           # mock implementations + process delegation
    plugins/        # Hangar / Modrinth / Spigot search + download
    process/        # real Java start/stop/restart + RCON
  api/              # FastAPI HTTP bridge for the web UI
  cli/              # main.py, gui.py, logging.py
  config.py
  models.py
web/                # React + Vite + TypeScript + Tailwind demo UI
tests/
docs/ARCHITECTURE.md   # why this structure
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full rationale.

## Architecture decisions (current)

| Piece | Choice |
|--------|--------|
| Package layout | **src/mcserver** (PyPA src layout) |
| LLM API | DeepSeek via OpenAI SDK |
| Router | **Not** an LLM — `orchestrator/service.py` |
| Info mode | `orchestrator/routing.py` — skip Verifier for Q&A |
| Tools today | `tools/stub/state.py` + `tools/plugins/` catalog + `tools/process/` |
| Install guardrail | **Prototype:** blocklist-only (`PLUGIN_BLOCKLIST`). Sources: hangar, modrinth, spigot. |
| Web UI | React + Vite + TypeScript + Tailwind in `web/` |
| HTTP API | FastAPI in `api/` wrapping `Orchestrator` (SSE logs) |

## How to run

1. Copy `.env.example` to `.env` once if you do not have `.env` yet, then set secrets (e.g. `DEEPSEEK_API_KEY`).
2. `uv sync`
3. CLI: `uv run mcserver "Install WorldEdit"` or Tkinter: `uv run mcserver-gui`
4. Web UI: `uv run mcserver-api` then `cd web && npm install && npm run dev`
5. Legacy: `uv run python main.py` / `gui.py` still work
6. Logs: `logs/YYYY-MM-DD_HH-MM-SS.log`

## Environment files

| File | Purpose |
|------|---------|
| `.env` | **Active config** for this machine. `config.py` loads this at runtime. |
| `.env.example` | Template for new clones only — placeholders, no secrets. |

When adding or changing env vars during development, **update `.env` first** so the app picks up changes immediately. Only touch `.env.example` when introducing a brand-new variable that future clones need documented (keep placeholders, never copy secrets). Do not commit `.env`.

## Test Server Environment

A real Paper Minecraft server (Minecraft 26.2) is installed locally in the `server/` folder for testing agent behavior.
- **Server Location:** `server/` (contains `server.jar`, `eula.txt` [EULA accepted], `start.bat`, and `start.sh`).
- **Usage:** Used to validate process control, RCON integration, and real plugin installations when transitioning away from the stub implementations.

## Next work

1. ~~Replace `tools/stub/` with real process control~~ — done: `tools/process/` (start/stop/restart).
2. ~~Wire real RCON for graceful stop when process was started outside this app~~ — done: `tools/process/rcon.py` + RCON fallback in `tools/process/manager.py`.
3. ~~Web UI demo (React + FastAPI)~~ — done: `web/` + `src/mcserver/api/`.
4. Optional: FastMCP wrapper around `tools/registry` for OpenClaw/Cursor.
5. Optional: LangGraph if orchestrator gains retries / human approval.
6. Optional: polish web UI (structured agent events, design system / shadcn, Tauri desktop shell).

## Future work

Suggested follow-ups from **plugin web discovery**. Each tagged `[plugin-discovery]` — review individually.

| Tag | Task | Notes |
| --- | ---- | ----- |
| `[plugin-discovery]` | **Production security hardening** | Re-enable search-session install gate; optional curated allowlist; review premium-plugin policy |
| `[plugin-discovery]` | **Semantic / embedding search** | LLM keyword translation is enough for v1; revisit if search quality is poor |
| `[plugin-discovery]` | **Plugin dependency resolution** | Auto-install deps when a plugin requires them |
| `[plugin-discovery]` | **Real plugin config on disk** | `configure_plugin` writes actual YAML/properties under `plugins/` |
| `[plugin-discovery]` | **FastMCP wrapper for catalog tools** | Expose search/download tools via MCP for OpenClaw/Cursor |
| `[plugin-discovery]` | **Auto-detect MC version** | Parse from server log or `version_history.json` instead of `MC_MINECRAFT_VERSION` |

## Process control

| Setting | Meaning |
|---------|---------|
| `MC_PROCESS_MODE=auto` (default) | Use real Java if `server.jar` exists under `MC_SERVER_DIR` |
| `MC_PROCESS_MODE=stub` | Fake start/stop (unit tests / no Java) |
| `MC_PROCESS_MODE=real` | Always use real process (fails if jar missing) |

Tools: `start_server`, `stop_server`, `restart_server` (Plugin Manager). PID file: `{MC_SERVER_DIR}/mcserver.pid`.

Graceful stop order: managed stdin → RCON `stop` → force kill by PID. If no PID file exists, `stop_server` can still stop externally launched servers via RCON when `MC_RCON_ENABLED=true`.

## Hard constraints

- Orchestrator is deterministic Python — never introduce an LLM router.
- Plugin Manager and Verifier keep **separate** prompts, tools, histories.
- Verifier write tool: `rollback_last_change` only.
