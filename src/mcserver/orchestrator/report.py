"""Format orchestrator results for CLI/GUI output."""

from __future__ import annotations

from mcserver.models import ChangeRecord, OrchestratorResult, VerifyResult


def _compact_change_record(cr: ChangeRecord) -> str:
    parts = [f"action={cr.action}"]
    if cr.target:
        parts.append(f"target={cr.target}")
    if cr.details:
        parts.append(f"details={cr.details}")
    return ", ".join(parts)


def print_result(result: OrchestratorResult) -> None:
    """Print one user-facing answer plus compact audit metadata."""
    status = "OK" if result.success else "FAILED"
    print(f"\n=== {status} ({result.mode} mode) ===")
    print(result.message)

    # Only show extra agent prose when it differs from the summary line.
    extra = (result.plugin_manager_reply or "").strip()
    if extra and extra != result.message.strip():
        print("\n--- Plugin Manager (detail) ---")
        print(extra)

    if result.change_record:
        print(f"\nchange_record: {_compact_change_record(result.change_record)}")

    if result.mode == "change" and result.verify_result:
        print(f"verify: {_format_verify(result.verify_result)}")

    if result.rolled_back:
        print("(rollback was performed)")


def _format_verify(v: VerifyResult) -> str:
    return f"healthy={v.healthy}, reason={v.reason}"
