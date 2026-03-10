import asyncio
import platform
from datetime import datetime, timezone, timedelta

import sqlalchemy
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.job import Job, JobExecution
from ..services import notifier
from ..services import scheduler as scheduler_svc

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(sqlalchemy.text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    sched = scheduler_svc.get_status()
    return {
        "status": "ok" if db_ok and sched["running"] else "degraded",
        "database": "ok" if db_ok else "error",
        "scheduler": sched,
        "platform": platform.system(),
        "python": platform.python_version(),
    }


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    day_ago = (now - timedelta(hours=24)).isoformat()

    total_jobs = db.query(Job).count()
    enabled_jobs = db.query(Job).filter(Job.is_enabled == True).count()  # noqa: E712
    running_jobs = db.query(Job).filter(Job.is_running == True).count()  # noqa: E712

    success_24h = db.query(JobExecution).filter(
        JobExecution.started_at >= day_ago,
        JobExecution.status == "success",
    ).count()
    failed_24h = db.query(JobExecution).filter(
        JobExecution.started_at >= day_ago,
        JobExecution.status.in_(["failed", "timeout", "killed"]),
    ).count()
    total_24h = db.query(JobExecution).filter(
        JobExecution.started_at >= day_ago
    ).count()

    return {
        "total_jobs": total_jobs,
        "enabled_jobs": enabled_jobs,
        "running_jobs": running_jobs,
        "executions_24h": total_24h,
        "success_24h": success_24h,
        "failed_24h": failed_24h,
    }


@router.get("/events")
async def sse_stream(request: Request):
    q = notifier.subscribe()

    async def generator():
        try:
            yield 'data: {"type": "connected"}\n\n'
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            notifier.unsubscribe(q)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
