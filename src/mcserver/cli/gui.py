"""Minimal tkinter GUI: enter a request, watch agent output, log to file."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from mcserver.cli.logging import RunLogger
from mcserver.orchestrator import Orchestrator
from mcserver.orchestrator.report import print_result
from mcserver.tools import stub_state


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Minecraft Server Manager")
        self.geometry("720x480")
        self.minsize(520, 360)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._busy = False
        self._run_logger: RunLogger | None = None

        self._build()
        self.after(100, self._drain_log_queue)

    def _build(self) -> None:
        pad = {"padx": 10, "pady": 6}

        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, **pad)

        ttk.Label(frm, text="Request").pack(anchor=tk.W)
        self.request_var = tk.StringVar()
        entry = ttk.Entry(frm, textvariable=self.request_var)
        entry.pack(fill=tk.X, pady=(0, 6))
        entry.bind("<Return>", lambda _e: self._on_run())

        opts = ttk.Frame(frm)
        opts.pack(fill=tk.X, pady=(0, 6))
        self.force_unhealthy = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts,
            text="Force unhealthy (stub rollback test)",
            variable=self.force_unhealthy,
        ).pack(side=tk.LEFT)

        self.run_btn = ttk.Button(opts, text="Run", command=self._on_run)
        self.run_btn.pack(side=tk.RIGHT)

        ttk.Label(frm, text="Output").pack(anchor=tk.W)
        self.output = scrolledtext.ScrolledText(
            frm,
            wrap=tk.WORD,
            height=18,
            state=tk.DISABLED,
            font=("Consolas", 10),
        )
        self.output.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(frm, textvariable=self.status_var).pack(anchor=tk.W, pady=(6, 0))

        entry.focus_set()

    def _append_output(self, text: str) -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def _drain_log_queue(self) -> None:
        try:
            while True:
                chunk = self._log_queue.get_nowait()
                self._append_output(chunk)
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def _on_run(self) -> None:
        if self._busy:
            return
        request = self.request_var.get().strip()
        if not request:
            messagebox.showinfo("Request", "Enter a request first.")
            return

        self._busy = True
        self.run_btn.configure(state=tk.DISABLED)
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.configure(state=tk.DISABLED)

        force = self.force_unhealthy.get()
        self.status_var.set("Running…")

        thread = threading.Thread(
            target=self._worker,
            args=(request, force),
            daemon=True,
        )
        thread.start()

    def _gui_sink(self, data: str) -> None:
        self._log_queue.put(data)

    def _worker(self, request: str, force_unhealthy: bool) -> None:
        logger = RunLogger()
        self._run_logger = logger
        logger.set_gui_sink(self._gui_sink)
        log_path = logger.start(header=f"request: {request}")
        self._log_queue.put(f"Log file: {log_path}\n\n")

        try:
            stub_state.ensure_mock_layout()
            stub_state.set_force_unhealthy(force_unhealthy)

            result = Orchestrator().handle(request)

            print_result(result)

            self.after(
                0,
                lambda: self.status_var.set(
                    f"{'OK' if result.success else 'FAILED'} ({result.mode}) — log: {log_path.name}"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"\nError: {type(exc).__name__}: {exc}")
            self.after(0, lambda: self.status_var.set(f"Error — log: {log_path.name}"))
        finally:
            logger.stop()
            self.after(0, self._finish_run)

    def _finish_run(self) -> None:
        self._busy = False
        self.run_btn.configure(state=tk.NORMAL)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
