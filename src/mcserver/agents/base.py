"""Minimal DeepSeek (OpenAI-compatible) tool-calling agent loop.

Each agent owns its own system prompt, tool list, and message history.
Tool bodies run in-process (stubs today; real shell/RCON later) — the model
only chooses which tool to call and with what arguments.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from openai import OpenAI

from mcserver import config

ToolFn = Callable[..., dict[str, Any]]


class ToolCallingAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: dict[str, ToolFn],
        tool_schemas: list[dict[str, Any]],
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_steps: int | None = None,
    ) -> None:
        self.name = name
        self.tools = tools
        self.tool_schemas = tool_schemas
        self.model = model or config.DEEPSEEK_MODEL
        self.max_steps = max_steps or config.MAX_AGENT_STEPS
        key = api_key if api_key is not None else config.DEEPSEEK_API_KEY
        if not key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        self.client = OpenAI(
            api_key=key,
            base_url=base_url or config.DEEPSEEK_BASE_URL,
        )
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

    def reset_history(self, system_prompt: str | None = None) -> None:
        """Drop conversation turns; keep (or replace) the system prompt."""
        sys = system_prompt or self.messages[0]["content"]
        self.messages = [{"role": "system", "content": sys}]

    def run(self, user_message: str) -> str:
        """Run a tool-calling loop until the model returns a final text answer."""
        self.messages.append({"role": "user", "content": user_message})

        for step in range(self.max_steps):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tool_schemas,
                tool_choice="auto",
            )
            choice = response.choices[0]
            message = choice.message

            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
            }
            if message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in message.tool_calls
                ]
            self.messages.append(assistant_msg)

            if not message.tool_calls:
                return (message.content or "").strip()

            for tc in message.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self._dispatch(name, args)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    }
                )
            print(f"[{self.name}] step {step + 1}: executed tool call(s)")

        return (
            f"[{self.name}] stopped after {self.max_steps} steps without a final answer."
        )

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        fn = self.tools.get(name)
        if fn is None:
            return {"ok": False, "error": f"Unknown tool: {name}"}
        try:
            print(f"[{self.name}] tool {name}({args})")
            return fn(**args)
        except TypeError as exc:
            return {"ok": False, "error": f"Bad arguments for {name}: {exc}"}
        except Exception as exc:  # noqa: BLE001 — surface tool failures to the model
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
