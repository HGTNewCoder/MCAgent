import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRequests } from "../api/client";
import type { RequestSummary } from "../api/types";
import { ResultCard } from "../components/ResultCard";

export default function HistoryPage() {
  const [items, setItems] = useState<RequestSummary[]>([]);
  const [selected, setSelected] = useState<RequestSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const data = await listRequests();
        setItems(data);
        setSelected(data[0] ?? null);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
  }, []);

  return (
    <div className="max-w-4xl space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">History</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Recent orchestrator runs from this API process. Run a request from{" "}
          <Link to="/" className="text-[var(--accent)] hover:underline">
            Request
          </Link>{" "}
          to populate this list.
        </p>
      </header>

      {error ? (
        <p className="text-sm text-[var(--danger)]">{error}</p>
      ) : null}

      {items.length === 0 && !error ? (
        <p className="text-sm text-[var(--muted)]">No runs yet.</p>
      ) : null}

      {items.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => setSelected(item)}
                  className={[
                    "w-full text-left rounded-lg border px-3 py-3 transition-colors",
                    selected?.id === item.id
                      ? "border-[var(--accent-dim)] bg-[var(--panel)]"
                      : "border-[var(--border)] hover:border-[var(--accent-dim)]",
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium truncate">
                      {item.request}
                    </span>
                    <span className="text-xs text-[var(--muted)] shrink-0">
                      {item.status}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    {new Date(item.created_at).toLocaleString()}
                  </p>
                </button>
              </li>
            ))}
          </ul>

          <div className="space-y-3">
            {selected?.result ? (
              <ResultCard result={selected.result} />
            ) : selected?.error ? (
              <p className="text-sm text-[var(--danger)]">{selected.error}</p>
            ) : selected ? (
              <p className="text-sm text-[var(--muted)]">
                No result yet (status: {selected.status}).
              </p>
            ) : null}
            {selected?.log_path ? (
              <p className="text-xs text-[var(--muted)] font-mono break-all">
                log: {selected.log_path}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
