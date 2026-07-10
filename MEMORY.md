# Project memory — two-agent Minecraft server management

Use this file (and `.cursor/rules/minecraft-two-agent.mdc`) to resume work in a new chat.

## Goal

Build a **two-agent** Minecraft server management system with a **deterministic orchestrator** (plain Python, **no LLM router**).

```
User request
  → Orchestrator (code)
  → Plugin Manager agent (DeepSeek + tools)
  → change_record
  → Verifier agent (DeepSeek + separate tools/history)
  → healthy? success report
     else: rollback + restart → failure report
```

## Architecture decisions (current)

| Piece | Choice |
|--------|--------|
| LLM API | DeepSeek via OpenAI SDK (`base_url=https://api.deepseek.com`) |
| Router | **Not** an LLM — `orchestrator.py` |
| Agent isolation | Separate system prompts, tool lists, message histories |
| Tools today | **Stubs** in `tools/stub_state.py` (mock FS + JSON state under `mock_server/`) |
| Tools later | Real subprocess / RCON / filesystem; same schemas, swap implementations |
| Install guardrail | `config.PLUGIN_ALLOWLIST` — `install_plugin` refuses non-allowlisted names |
| Verifier writes | Only `rollback_last_change` (plus restart as part of rollback) |

## Key files

- `main.py` — CLI (`--gui` opens the window)
- `gui.py` — minimal tkinter UI for requests + live output
- `run_log.py` — tees stdout/stderr into `logs/YYYY-MM-DD_HH-MM-SS.log`
- `orchestrator.py` — deterministic flow
- `config.py` — API keys, paths, allowlist (`RUN_LOGS_DIR`)
- `models.py` — `ChangeRecord`, `VerifyResult`, `OrchestratorResult`
- `agents/base.py` — DeepSeek tool-calling loop
- `agents/plugin_manager.py` — Agent 1
- `agents/verifier.py` — Agent 2
- `tools/plugin_tools.py` / `tools/verifier_tools.py` — schemas + dispatch maps
- `tools/stub_state.py` — stub implementations + `mock_server/` state

## change_record / verify contracts

```json
// Plugin Manager → Verifier
{"action":"install|uninstall|configure|noop","target":"...","backup_path":"...","timestamp":"...","details":"..."}

// Verifier → Orchestrator
{"healthy": true, "reason": "..."}
```

## How to run

1. `cp .env.example .env` and set `DEEPSEEK_API_KEY`
2. `uv sync` (or install deps from `pyproject.toml`)
3. GUI: `uv run python gui.py` (or `uv run python main.py --gui`)
4. CLI: `uv run python main.py "Install WorldEdit"`
5. Rollback path: `uv run python main.py --force-unhealthy "Install LuckPerms"`
6. Logs: every run creates `logs/YYYY-MM-DD_HH-MM-SS.log`

## Next work (not done yet)

1. Replace stub bodies with real Paper/Spigot/Purpur process control + RCON.
2. Persist allowlist / vetted repo metadata outside `config.py` if needed.
3. Wire real log paths and smoke-test timing (`SMOKE_TEST_SECONDS`).
4. Optional: dry-run mode, audit log of change_records.

## Explicit non-goals (for now)

- No LLM-based routing between agents
- No shared message history between Plugin Manager and Verifier
- No installing plugins outside the allowlist
