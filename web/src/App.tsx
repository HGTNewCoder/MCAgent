import { NavLink, Route, Routes } from "react-router-dom";
import HistoryPage from "./pages/HistoryPage";
import PluginsPage from "./pages/PluginsPage";
import RequestPage from "./pages/RequestPage";
import ServerPage from "./pages/ServerPage";

const nav = [
  { to: "/", label: "Request" },
  { to: "/server", label: "Server" },
  { to: "/plugins", label: "Plugins" },
  { to: "/history", label: "History" },
];

export default function App() {
  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <aside className="md:w-56 shrink-0 border-b md:border-b-0 md:border-r border-[var(--border)] bg-[color-mix(in_srgb,var(--panel)_88%,transparent)] backdrop-blur-sm">
        <div className="px-5 py-5">
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
            mcserver
          </p>
          <h1 className="mt-1 text-lg font-semibold leading-tight">
            Server Manager
          </h1>
        </div>
        <nav className="flex md:flex-col gap-1 px-3 pb-4 overflow-x-auto">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                [
                  "rounded-md px-3 py-2 text-sm whitespace-nowrap transition-colors",
                  isActive
                    ? "bg-[color-mix(in_srgb,var(--accent)_18%,transparent)] text-[var(--accent)]"
                    : "text-[var(--muted)] hover:text-[var(--text)] hover:bg-[color-mix(in_srgb,var(--panel)_60%,#000)]",
                ].join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="flex-1 min-w-0 p-4 md:p-8">
        <Routes>
          <Route path="/" element={<RequestPage />} />
          <Route path="/server" element={<ServerPage />} />
          <Route path="/plugins" element={<PluginsPage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </main>
    </div>
  );
}
