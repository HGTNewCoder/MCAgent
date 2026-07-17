"""FastAPI application wrapping the deterministic Orchestrator."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from mcserver import config
from mcserver.api.jobs import JobStatus, job_store, start_job
from mcserver.tools import stub_state


class CreateRequestBody(BaseModel):
    request: str = Field(..., min_length=1)
    force_unhealthy: bool = False


def create_app() -> FastAPI:
    app = FastAPI(
        title="Minecraft Server Manager API",
        version="0.1.0",
        description="HTTP bridge over the deterministic Orchestrator for the web UI.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/requests")
    def create_request(body: CreateRequestBody) -> dict[str, Any]:
        text = body.request.strip()
        if not text:
            raise HTTPException(status_code=400, detail="request must not be empty")
        job = job_store.create(text, force_unhealthy=body.force_unhealthy)
        start_job(job)
        return {"id": job.id, "status": job.status.value}

    @app.get("/api/requests")
    def list_requests() -> dict[str, Any]:
        return {"items": job_store.history()}

    @app.get("/api/requests/{job_id}")
    def get_request(job_id: str) -> dict[str, Any]:
        job = job_store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="request not found")
        return job.to_summary()

    @app.get("/api/requests/{job_id}/events")
    async def request_events(job_id: str) -> StreamingResponse:
        job = job_store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="request not found")

        async def event_stream():
            index = 0
            while True:
                chunks, index = job.snapshot_logs_from(index)
                for chunk in chunks:
                    payload = json.dumps({"type": "log", "data": chunk})
                    yield f"data: {payload}\n\n"

                if job.status in (JobStatus.DONE, JobStatus.ERROR) and job._done.is_set():
                    # Flush any final log chunks written after status flip
                    chunks, index = job.snapshot_logs_from(index)
                    for chunk in chunks:
                        payload = json.dumps({"type": "log", "data": chunk})
                        yield f"data: {payload}\n\n"
                    done_payload = json.dumps(
                        {
                            "type": "done",
                            "status": job.status.value,
                            "result": job.result,
                            "error": job.error,
                            "log_path": job.log_path,
                        }
                    )
                    yield f"data: {done_payload}\n\n"
                    break

                await asyncio.sleep(0.1)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/server/status")
    def server_status() -> dict[str, Any]:
        stub_state.ensure_mock_layout()
        alive = stub_state.check_process_alive()
        return {
            "alive": bool(alive.get("alive")),
            "pid": alive.get("pid"),
            "server_dir": str(config.SERVER_DIR),
            "process_mode": config.MC_PROCESS_MODE,
            "ok": bool(alive.get("ok", True)),
            "raw": alive,
        }

    @app.post("/api/server/{action}")
    def server_action(action: Literal["start", "stop", "restart"]) -> dict[str, Any]:
        stub_state.ensure_mock_layout()
        if action == "start":
            result = stub_state.start_server()
        elif action == "stop":
            result = stub_state.stop_server()
        else:
            result = stub_state.restart_server()
        return {"action": action, **result}

    @app.get("/api/plugins")
    def list_plugins() -> dict[str, Any]:
        return stub_state.list_plugins_info()

    return app


app = create_app()
