import type { OrchestratorResult } from "../api/types";

export function ResultCard({ result }: { result: OrchestratorResult }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={
            result.success
              ? "text-[var(--accent)] font-medium"
              : "text-[var(--danger)] font-medium"
          }
        >
          {result.success ? "OK" : "FAILED"}
        </span>
        <span className="text-xs uppercase tracking-wide text-[var(--muted)]">
          {result.mode} mode
        </span>
        {result.rolled_back ? (
          <span className="text-xs text-[var(--warn)]">rolled back</span>
        ) : null}
      </div>
      <p className="text-sm whitespace-pre-wrap">{result.message}</p>
      {result.change_record ? (
        <pre className="text-xs text-[var(--muted)] overflow-x-auto">
          change_record: {JSON.stringify(result.change_record, null, 2)}
        </pre>
      ) : null}
      {result.verify_result ? (
        <pre className="text-xs text-[var(--muted)] overflow-x-auto">
          verify: {JSON.stringify(result.verify_result, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
