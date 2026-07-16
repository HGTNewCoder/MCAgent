"""CLI entrypoint for the two-agent Minecraft server management system."""

from __future__ import annotations

import argparse
import json
import sys

from mcserver.cli.gui import main as gui_main
from mcserver.cli.logging import RunLogger
from mcserver.orchestrator import Orchestrator
from mcserver.orchestrator.report import print_result
from mcserver.tools import stub_state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Minecraft server management: Plugin Manager + Verifier (DeepSeek)."
    )
    parser.add_argument(
        "request",
        nargs="?",
        help='User request, e.g. "Install WorldEdit"',
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open the minimal GUI instead of the terminal prompt.",
    )
    parser.add_argument(
        "--force-unhealthy",
        action="store_true",
        help="Stub only: make health checks fail so you can exercise rollback.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print OrchestratorResult as JSON.",
    )
    args = parser.parse_args(argv)

    if args.gui:
        gui_main()
        return 0

    request = args.request
    if not request:
        request = input("Request> ").strip()
    if not request:
        print("No request provided.", file=sys.stderr)
        return 2

    logger = RunLogger()
    log_path = logger.start(header=f"request: {request}")
    print(f"Log file: {log_path}")

    try:
        stub_state.ensure_mock_layout()
        if args.force_unhealthy:
            stub_state.set_force_unhealthy(True)

        result = Orchestrator().handle(request)

        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print_result(result)

        return 0 if result.success else 1
    finally:
        logger.stop()
        print(f"Saved log: {log_path}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
