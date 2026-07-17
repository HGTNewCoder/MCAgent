"""In-memory request jobs with log streaming for the web API."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from mcserver.cli.logging import RunLogger
from mcserver.models import OrchestratorResult
from mcserver.orchestrator import Orchestrator
from mcserver.orchestrator.report import print_result
from mcserver.tools import stub_state


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class RequestJob:
    id: str
    request: str
    force_unhealthy: bool
    status: JobStatus = JobStatus.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    log_path: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    _log_chunks: list[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _done: threading.Event = field(default_factory=threading.Event)

    def append_log(self, data: str) -> None:
        with self._lock:
            self._log_chunks.append(data)

    def snapshot_logs_from(self, index: int) -> tuple[list[str], int]:
        with self._lock:
            chunks = self._log_chunks[index:]
            return chunks, len(self._log_chunks)

    def to_summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "request": self.request,
            "force_unhealthy": self.force_unhealthy,
            "status": self.status.value,
            "created_at": self.created_at,
            "log_path": self.log_path,
            "result": self.result,
            "error": self.error,
        }


class JobStore:
    """Thread-safe store of recent orchestrator runs."""

    def __init__(self, max_history: int = 50) -> None:
        self._jobs: dict[str, RequestJob] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()
        self._max_history = max_history

    def create(self, request: str, force_unhealthy: bool = False) -> RequestJob:
        job = RequestJob(
            id=str(uuid.uuid4()),
            request=request,
            force_unhealthy=force_unhealthy,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._order.append(job.id)
            while len(self._order) > self._max_history:
                old_id = self._order.pop(0)
                self._jobs.pop(old_id, None)
        return job

    def get(self, job_id: str) -> RequestJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = [self._jobs[i] for i in reversed(self._order) if i in self._jobs]
        return [j.to_summary() for j in jobs]


job_store = JobStore()

# RunLogger swaps the process-global sys.stdout/sys.stderr, so only one run may
# manipulate them at a time. Serialize orchestrator runs to keep their captured
# output from interleaving (matches the deterministic single-run architecture).
_run_lock = threading.Lock()


def start_job(job: RequestJob) -> None:
    """Run Orchestrator in a background thread; tee stdout into the job log."""

    def worker() -> None:
        with _run_lock:
            job.status = JobStatus.RUNNING
            logger = RunLogger()
            logger.set_gui_sink(job.append_log)
            log_path = logger.start(header=f"request: {job.request}")
            job.log_path = str(log_path)
            job.append_log(f"Log file: {log_path}\n\n")

            try:
                stub_state.ensure_mock_layout()
                stub_state.set_force_unhealthy(job.force_unhealthy)
                result: OrchestratorResult = Orchestrator().handle(job.request)
                print_result(result)
                job.result = result.to_dict()
                job.status = JobStatus.DONE
            except Exception as exc:  # noqa: BLE001
                job.error = f"{type(exc).__name__}: {exc}"
                job.append_log(f"\nError: {job.error}\n")
                job.status = JobStatus.ERROR
            finally:
                logger.stop()
                job._done.set()

    threading.Thread(target=worker, daemon=True).start()
