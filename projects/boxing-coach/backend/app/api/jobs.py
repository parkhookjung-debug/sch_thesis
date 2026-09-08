"""In-memory job 트래킹. 단일 프로세스 MVP 가정.

본격 배포에서는 Redis/RQ/Celery 같은 큐로 대체할 것.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

JobStatus = Literal["pending", "running", "done", "failed"]


@dataclass
class Job:
    id: str
    kind: str
    status: JobStatus = "pending"
    progress: float = 0.0      # 0.0 ~ 1.0
    progress_label: str = ""
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


_lock = threading.Lock()
_jobs: dict[str, Job] = {}


def create_job(kind: str) -> Job:
    with _lock:
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, kind=kind)
        _jobs[job_id] = job
        return job


def get_job(job_id: str) -> Optional[Job]:
    with _lock:
        return _jobs.get(job_id)


def update_job(job_id: str, **fields: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        for k, v in fields.items():
            setattr(job, k, v)
        job.updated_at = time.time()


def progress_updater(job_id: str, label: str = ""):
    """Returns a callback(current, total) → updates job progress."""
    def _cb(cur: int, total: int) -> None:
        pct = (cur / total) if total else 0.0
        update_job(job_id, progress=round(min(pct, 1.0), 4), progress_label=label or f"{cur}/{total}")
    return _cb
