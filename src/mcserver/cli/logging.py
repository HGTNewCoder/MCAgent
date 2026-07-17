"""Session logging: tee stdout/stderr into a datetime-named log file.

The tee swaps the process-global ``sys.stdout`` / ``sys.stderr``. To stay safe
when runs are triggered from background threads (e.g. the web API), every
``_TeeStream`` wraps the *true* original streams rather than whatever happens to
be installed at construction time. This prevents tees from chaining into one
another, which previously caused ``ValueError: I/O operation on closed file``
when one run closed its log file while another still referenced it.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO, Callable

from mcserver import config

# The genuine interpreter streams, captured once before any tee is installed.
_REAL_STDOUT: TextIO = sys.stdout
_REAL_STDERR: TextIO = sys.stderr


class _TeeStream:
    """Write to the original stream and optional extra sinks (log file, GUI)."""

    def __init__(self, primary: TextIO, *sinks: Callable[[str], None]) -> None:
        self._primary = primary
        self._sinks = list(sinks)

    def write(self, data: str) -> int:
        if not data:
            return 0
        try:
            self._primary.write(data)
            self._primary.flush()
        except (ValueError, OSError):
            # Underlying stream closed/detached; keep feeding the other sinks.
            pass
        for sink in self._sinks:
            try:
                sink(data)
            except (ValueError, OSError):
                pass
        return len(data)

    def flush(self) -> None:
        try:
            self._primary.flush()
        except (ValueError, OSError):
            pass

    def fileno(self) -> int:
        return self._primary.fileno()

    def isatty(self) -> bool:
        try:
            return self._primary.isatty()
        except (ValueError, OSError):
            return False


class RunLogger:
    """One log file per run: logs/YYYY-MM-DD_HH-MM-SS.log"""

    def __init__(self, log_dir: Path | None = None) -> None:
        self.log_dir = log_dir or config.RUN_LOGS_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.path = self.log_dir / f"{stamp}.log"
        self._file = self.path.open("w", encoding="utf-8")
        # Always restore to / wrap the genuine streams, never another tee.
        self._orig_stdout = _REAL_STDOUT
        self._orig_stderr = _REAL_STDERR
        self._gui_sink: Callable[[str], None] | None = None
        self._active = False
        self._closed = False
        self._tee_stdout: _TeeStream | None = None
        self._tee_stderr: _TeeStream | None = None

    def set_gui_sink(self, sink: Callable[[str], None] | None) -> None:
        self._gui_sink = sink
        if self._active:
            self._install_tees()

    def start(self, header: str = "") -> Path:
        self._file.write(f"=== run started {datetime.now().isoformat()} ===\n")
        if header:
            self._file.write(header.rstrip() + "\n")
            self._file.write("\n")
        self._file.flush()
        self._install_tees()
        self._active = True
        return self.path

    def _install_tees(self) -> None:
        sinks: list[Callable[[str], None]] = [self._write_file]
        if self._gui_sink is not None:
            sinks.append(self._gui_sink)
        self._tee_stdout = _TeeStream(self._orig_stdout, *sinks)
        self._tee_stderr = _TeeStream(self._orig_stderr, *sinks)
        sys.stdout = self._tee_stdout  # type: ignore[assignment]
        sys.stderr = self._tee_stderr  # type: ignore[assignment]

    def _write_file(self, data: str) -> None:
        if self._closed:
            return
        try:
            self._file.write(data)
            self._file.flush()
        except (ValueError, OSError):
            pass

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        # Only restore if our tee is still the installed stream; otherwise a
        # concurrent logger owns it and we must not clobber its redirection.
        if sys.stdout is self._tee_stdout:
            sys.stdout = self._orig_stdout
        if sys.stderr is self._tee_stderr:
            sys.stderr = self._orig_stderr
        if not self._closed:
            try:
                self._file.write(
                    f"\n=== run ended {datetime.now().isoformat()} ===\n"
                )
                self._file.flush()
            except (ValueError, OSError):
                pass
            finally:
                self._closed = True
                try:
                    self._file.close()
                except (ValueError, OSError):
                    pass

    def __enter__(self) -> RunLogger:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()
