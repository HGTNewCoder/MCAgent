import { useCallback, useEffect, useState } from "react";
import { getServerStatus, serverAction } from "../api/client";
import type { ServerStatus } from "../api/types";

export default function ServerPage() {
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      setStatus(await getServerStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(id);
  }, [refresh]);

  async function run(action: "start" | "stop" | "restart") {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await serverAction(action);
      setMessage(`${action}: ${JSON.stringify(result)}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">Server</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Start, stop, or restart the Minecraft process via the same tools the
          agents use.
        </p>
      </header>

      <div className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={
              status?.alive
                ? "inline-flex h-2.5 w-2.5 rounded-full bg-[var(--accent)]"
                : "inline-flex h-2.5 w-2.5 rounded-full bg-[var(--danger)]"
            }
          />
          <span className="font-medium">
            {status == null
              ? "Loading…"
              : status.alive
                ? "Running"
                : "Stopped"}
          </span>
          {status?.pid != null ? (
            <span className="text-sm text-[var(--muted)]">pid {status.pid}</span>
          ) : null}
        </div>

        {status ? (
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[var(--muted)]">Process mode</dt>
              <dd>{status.process_mode}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-[var(--muted)]">Server dir</dt>
              <dd className="font-mono text-xs break-all">{status.server_dir}</dd>
            </div>
          </dl>
        ) : null}

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => void run("start")}
            className="rounded-md border border-[var(--border)] px-3 py-2 text-sm hover:border-[var(--accent-dim)] disabled:opacity-50"
          >
            Start
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void run("stop")}
            className="rounded-md border border-[var(--border)] px-3 py-2 text-sm hover:border-[var(--danger)] disabled:opacity-50"
          >
            Stop
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void run("restart")}
            className="rounded-md border border-[var(--border)] px-3 py-2 text-sm hover:border-[var(--warn)] disabled:opacity-50"
          >
            Restart
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void refresh()}
            className="rounded-md px-3 py-2 text-sm text-[var(--muted)] hover:text-[var(--text)]"
          >
            Refresh
          </button>
        </div>
      </div>

      {message ? (
        <pre className="text-xs text-[var(--muted)] overflow-x-auto whitespace-pre-wrap">
          {message}
        </pre>
      ) : null}
      {error ? (
        <p className="text-sm text-[var(--danger)]">{error}</p>
      ) : null}
    </div>
  );
}
