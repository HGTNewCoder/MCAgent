import { useRef, useState, type FormEvent } from "react";
import { createRequest, streamRequestEvents } from "../api/client";
import type { OrchestratorResult } from "../api/types";
import { ResultCard } from "../components/ResultCard";

type RunStatus = "ready" | "running" | "done" | "error";

export default function RequestPage() {
  const [request, setRequest] = useState("Install WorldEdit");
  const [forceUnhealthy, setForceUnhealthy] = useState(false);
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState<RunStatus>("ready");
  const [statusLabel, setStatusLabel] = useState("Ready");
  const [result, setResult] = useState<OrchestratorResult | null>(null);
  const closeRef = useRef<(() => void) | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = request.trim();
    if (!text || status === "running") return;

    closeRef.current?.();
    setOutput("");
    setResult(null);
    setStatus("running");
    setStatusLabel("Running…");

    try {
      const { id } = await createRequest(text, forceUnhealthy);
      closeRef.current = streamRequestEvents(
        id,
        (event) => {
          if (event.type === "log") {
            setOutput((prev) => prev + event.data);
            return;
          }
          if (event.result) {
            setResult(event.result);
            setStatus("done");
            setStatusLabel(
              `${event.result.success ? "OK" : "FAILED"} (${event.result.mode})` +
                (event.log_path ? ` — ${event.log_path}` : ""),
            );
          } else {
            setStatus("error");
            setStatusLabel(event.error ?? "Error");
          }
        },
        (err) => {
          setStatus("error");
          setStatusLabel(err.message);
        },
      );
    } catch (err) {
      setStatus("error");
      setStatusLabel(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="max-w-4xl space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">Request</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Send a natural-language request through the orchestrator. Live agent
          output streams below.
        </p>
      </header>

      <form onSubmit={onSubmit} className="space-y-4">
        <label className="block space-y-2">
          <span className="text-sm text-[var(--muted)]">Request</span>
          <input
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            className="w-full rounded-md border border-[var(--border)] bg-[var(--panel)] px-3 py-2 text-sm outline-none focus:border-[var(--accent-dim)]"
            placeholder="Install WorldEdit"
            disabled={status === "running"}
          />
        </label>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
            <input
              type="checkbox"
              checked={forceUnhealthy}
              onChange={(e) => setForceUnhealthy(e.target.checked)}
              disabled={status === "running"}
            />
            Force unhealthy (stub rollback test)
          </label>
          <button
            type="submit"
            disabled={status === "running" || !request.trim()}
            className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[#062016] disabled:opacity-50 hover:brightness-110"
          >
            {status === "running" ? "Running…" : "Run"}
          </button>
        </div>
      </form>

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Output</h3>
          <span className="text-xs text-[var(--muted)]">{statusLabel}</span>
        </div>
        <pre className="h-[28rem] overflow-auto rounded-lg border border-[var(--border)] bg-[#0a0f14] p-4 text-xs leading-relaxed font-mono whitespace-pre-wrap">
          {output || "—"}
        </pre>
      </section>

      {result ? <ResultCard result={result} /> : null}
    </div>
  );
}
