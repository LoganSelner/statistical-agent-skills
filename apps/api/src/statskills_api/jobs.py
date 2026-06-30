"""In-process job registry for analysis runs (ROADMAP §11).

An agent run is many sandboxed steps over seconds to minutes, so it cannot be a blocking
request: submitting a run creates a :class:`Job`, a worker thread executes it, and the
client streams the job's :class:`~statskills_api.stream.RunTap` and later fetches the
report. At single-user research scale an in-process registry + a bounded-concurrency
semaphore suffice — no Celery/Redis (the §11 decision). The registry is thread-safe; one
process holds it, so jobs live for the process lifetime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
import uuid

from statskills.reporting import Report
from statskills_api.stream import RunTap


class JobStatus(str, Enum):
    """Lifecycle of a run, polled via ``GET /runs/{id}``."""

    RUNNING = "running"
    COMPOSING = "composing"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    """One submitted analysis run and its evolving result."""

    id: str
    out_dir: Path
    tap: RunTap = field(default_factory=RunTap)
    status: JobStatus = JobStatus.RUNNING
    report: Report | None = None
    error: str | None = None


class JobRegistry:
    """Thread-safe store of jobs + a bounded-concurrency gate on active runs."""

    def __init__(self, max_concurrent: int = 4) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(max_concurrent)

    def create(self, out_dir: Path) -> Job:
        job = Job(id=uuid.uuid4().hex, out_dir=out_dir)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def try_acquire_slot(self) -> bool:
        """Reserve a concurrency slot without blocking; ``False`` if at capacity."""
        return self._slots.acquire(blocking=False)

    def release_slot(self) -> None:
        self._slots.release()
