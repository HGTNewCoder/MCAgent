"""Session logging: tee stdout/stderr into a datetime-named log file."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO, Callable

from mcserver import config


class _TeeStream:
    """Write to the original stream and optional extra sinks (log file, GUI)."""

    def __init__(self, primary: TextIO, *sinks: Callable[[str], None]) -> None:
        self._primary = primary
        self._sinks = list(sinks)

    def write(self, data: str) -> int:
        if not data:
            return 0
        self._primary.write(data)
        self._primary.flush()
        for sink in self._sinks:
            sink(data)
        return len(data)

    def flush(self) -> None:
        self._primary.flush()

    def fileno(self) -> int:
        return self._primary.fileno()

    def isatty(self) -> bool:
        return self._primary.isatty()


class RunLogger:
    """One log file per run: logs/YYYY-MM-DD_HH-MM-SS.log"""

    def __init__(self, log_dir: Path | None = None) -> None:
        self.log_dir = log_dir or config.RUN_LOGS_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.path = self.log_dir / f"{stamp}.log"
        self._file = self.path.open("w", encoding="utf-8")
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        self._gui_sink: Callable[[str], None] | None = None
        self._active = False

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
        sys.stdout = _TeeStream(self._stdout, *sinks)  # type: ignore[assignment]
        sys.stderr = _TeeStream(self._stderr, *sinks)  # type: ignore[assignment]

    def _write_file(self, data: str) -> None:
        self._file.write(data)
        self._file.flush()

    def stop(self) -> None:
        if not self._active:
            return
        sys.stdout = self._stdout
        sys.stderr = self._stderr
        self._file.write(f"\n=== run ended {datetime.now().isoformat()} ===\n")
        self._file.flush()
        self._file.close()
        self._active = False

    def __enter__(self) -> RunLogger:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()
