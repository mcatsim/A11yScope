"""Scan queue manager -- sequential per API key, parallel across keys.

Each API key gets its own asyncio worker coroutine. Jobs for the same
key are processed in FIFO order. Different keys run concurrently.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class QueuedJob:
    job_id: str
    user_id: str
    api_key_id: str
    canvas_url: str
    course_id: int
    course_name: str
    status: str = "queued"  # queued, running, complete, failed, cancelled
    progress_pct: int = 0
    current_phase: str | None = None
    current_item: str | None = None
    items_total: int = 0
    items_checked: int = 0
    issues_found: int = 0
    error: str | None = None
    result: Any = None  # CourseAuditResult when complete
    progress_log: list[dict[str, Any]] = field(default_factory=list)
    db_session_factory: Any = None
    decrypt_fn: Callable | None = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ScanQueueManager:
    """Manages scan execution with per-key sequential processing."""

    def __init__(self) -> None:
        self._jobs: dict[str, QueuedJob] = {}
        self._key_queues: dict[str, asyncio.Queue[str]] = {}
        self._workers: dict[str, asyncio.Task] = {}

    async def enqueue(
        self,
        user_id: str,
        api_key_id: str,
        canvas_url: str,
        course_id: int,
        course_name: str,
        db_session_factory: Any,
        decrypt_fn: Callable,
    ) -> str:
        """Add a scan job to the queue. Returns job_id."""
        job_id = uuid.uuid4().hex[:12]
        job = QueuedJob(
            job_id=job_id,
            user_id=user_id,
            api_key_id=api_key_id,
            canvas_url=canvas_url,
            course_id=course_id,
            course_name=course_name,
            db_session_factory=db_session_factory,
            decrypt_fn=decrypt_fn,
        )
        self._jobs[job_id] = job

        # Ensure a queue + worker exists for this key
        if api_key_id not in self._key_queues:
            self._key_queues[api_key_id] = asyncio.Queue()
            self._workers[api_key_id] = asyncio.create_task(
                self._worker_loop(api_key_id)
            )

        await self._key_queues[api_key_id].put(job_id)
        logger.info(
            "Enqueued job %s for key %s (course %d)",
            job_id, api_key_id[:8], course_id,
        )
        return job_id

    async def _worker_loop(self, api_key_id: str) -> None:
        """Process jobs for a single API key sequentially."""
        queue = self._key_queues[api_key_id]
        while True:
            job_id = await queue.get()
            job = self._jobs.get(job_id)
            if not job or job.status == "cancelled":
                queue.task_done()
                continue
            try:
                job.status = "running"
                await self._execute_job(job_id)
            except Exception as exc:
                logger.exception("Job %s failed", job_id)
                if job_id in self._jobs:
                    self._jobs[job_id].status = "failed"
                    self._jobs[job_id].error = str(exc)
            finally:
                queue.task_done()

    async def _execute_job(self, job_id: str, **kwargs: Any) -> None:
        """Run the actual audit via audit_runner.run_audit().

        Decrypts the API key, creates an AuditJob for the session layer,
        wires up a progress callback that updates the QueuedJob fields
        and progress_log, then dereferences the key after completion.
        """
        from a11yscope.web.audit_runner import run_audit
        from a11yscope.web.session import AuditJob, JobStatus

        job = self._jobs[job_id]
        api_token: str | None = None

        try:
            # Decrypt the API key
            if job.decrypt_fn is not None:
                api_token = job.decrypt_fn(job.api_key_id)
            else:
                raise ValueError("No decrypt function provided for job")

            if not api_token:
                raise ValueError("Failed to decrypt API token")

            # Create an AuditJob for the session-layer audit runner
            audit_job = AuditJob(
                job_id=job.job_id,
                course_id=job.course_id,
                user_id=job.user_id,
                course_name=job.course_name,
            )

            # Progress callback: updates QueuedJob fields and appends to log
            async def on_progress(msg: dict[str, Any]) -> None:
                # Check for cancellation
                if job.cancel_event.is_set():
                    raise asyncio.CancelledError("Job cancelled by user")

                # Append to progress log for WebSocket replay
                job.progress_log.append(msg)

                msg_type = msg.get("type")

                if msg_type == "phase":
                    job.current_phase = msg.get("phase")
                elif msg_type == "item_found":
                    job.items_total = msg.get("count", 0)
                elif msg_type == "item_start":
                    job.current_item = msg.get("title")
                elif msg_type in ("item_checked", "item_done"):
                    job.items_checked = msg.get("checked", msg.get("index", job.items_checked))
                elif msg_type == "stats":
                    job.progress_pct = msg.get("progress_pct", job.progress_pct)
                    job.items_checked = msg.get("items_checked", job.items_checked)
                    job.issues_found = msg.get("issues_found", job.issues_found)
                    job.items_total = msg.get("items_total", job.items_total)
                elif msg_type == "file_checked":
                    pass  # Already handled by stats
                elif msg_type == "complete":
                    job.progress_pct = 100
                elif msg_type == "error":
                    logger.warning("Audit error for job %s: %s", job_id, msg.get("message"))

            # Run the audit
            result = await run_audit(
                job=audit_job,
                canvas_base_url=job.canvas_url,
                canvas_api_token=api_token,
                on_progress=on_progress,
            )

            # Store result and mark complete
            job.result = result
            job.status = "complete"
            job.progress_pct = 100
            job.current_phase = "complete"
            job.current_item = None

        except asyncio.CancelledError:
            job.status = "cancelled"
            job.progress_log.append({"type": "error", "message": "Scan cancelled"})
            logger.info("Job %s cancelled", job_id)
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.progress_log.append({"type": "error", "message": str(exc)})
            raise
        finally:
            # Dereference the decrypted key from memory
            api_token = None  # noqa: F841

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Get current status of a job."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        return {
            "job_id": job.job_id,
            "status": job.status,
            "course_id": job.course_id,
            "course_name": job.course_name,
            "progress_pct": job.progress_pct,
            "current_phase": job.current_phase,
            "current_item": job.current_item,
            "items_total": job.items_total,
            "items_checked": job.items_checked,
            "issues_found": job.issues_found,
            "error": job.error,
        }

    def cancel(self, job_id: str) -> bool:
        """Cancel a job. Returns True if cancelled."""
        job = self._jobs.get(job_id)
        if not job:
            return False
        if job.status in ("complete", "failed"):
            return False
        job.status = "cancelled"
        job.cancel_event.set()
        return True

    def get_user_jobs(self, user_id: str) -> list[dict[str, Any]]:
        """Get all jobs for a user."""
        return [
            self.get_job_status(jid)
            for jid, j in self._jobs.items()
            if j.user_id == user_id
        ]

    def get_queue_for_key(self, api_key_id: str) -> list[str]:
        """Get ordered list of queued job IDs for a key."""
        return [
            jid for jid, j in self._jobs.items()
            if j.api_key_id == api_key_id and j.status == "queued"
        ]
