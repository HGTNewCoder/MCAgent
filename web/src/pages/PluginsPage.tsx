import { useEffect, useState } from "react";
import { getPlugins } from "../api/client";
import type { PluginsInfo } from "../api/types";

export default function PluginsPage() {
  const [info, setInfo] = useState<PluginsInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setInfo(await getPlugins());
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
  }, []);

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">Plugins</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Catalog sources, blocklist, and what is currently installed / on disk.
        </p>
      </header>

      {error ? (
        <p className="text-sm text-[var(--danger)]">{error}</p>
      ) : null}

      {!info && !error ? (
        <p className="text-sm text-[var(--muted)]">Loading…</p>
      ) : null}

      {info ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <PluginList title="Allowed sources" items={info.allowed_sources} />
          <PluginList title="Blocklist" items={info.blocklist} />
          <PluginList title="Loaded (stub state)" items={info.loaded} />
          <PluginList title="JARs on disk" items={info.jars} />
        </div>
      ) : null}
    </div>
  );
}

function PluginList({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-4">
      <h3 className="text-sm font-medium mb-3">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">None</p>
      ) : (
        <ul className="space-y-1.5">
          {items.map((name) => (
            <li
              key={name}
              className="rounded border border-[var(--border)] px-2.5 py-1.5 text-sm font-mono"
            >
              {name}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
