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
    stub/           # mock implementations → replace with rcon/ later
  cli/              # main.py, gui.py, logging.py
  config.py
  models.py
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
| Tools today | Stubs in `tools/stub/state.py` |
| Install guardrail | `config.PLUGIN_ALLOWLIST` |

## How to run

1. `cp .env.example .env` and set `DEEPSEEK_API_KEY`
2. `uv sync`
3. `uv run mcserver "Install WorldEdit"` or `uv run mcserver-gui`
4. Legacy: `uv run python main.py` / `gui.py` still work
5. Logs: `logs/YYYY-MM-DD_HH-MM-SS.log`

## Next work

1. Replace `tools/stub/` with real process control + RCON.
2. Optional: FastMCP wrapper around `tools/registry` for OpenClaw/Cursor.
3. Optional: LangGraph if orchestrator gains retries / human approval.

## Hard constraints

- Orchestrator is deterministic Python — never introduce an LLM router.
- Plugin Manager and Verifier keep **separate** prompts, tools, histories.
- Verifier write tool: `rollback_last_change` only.
