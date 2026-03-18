"""APScheduler wrapper — manages job lifecycle."""
import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from ..config import settings

logger = logging.getLogger(__name__)

scheduler_instance: Optional[BackgroundScheduler] = None


def _make_scheduler() -> BackgroundScheduler:
    executors = {"default": ThreadPoolExecutor(max_workers=settings.max_concurrent_jobs)}
    job_defaults = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 60}
    return BackgroundScheduler(executors=executors, job_defaults=job_defaults)


def start() -> None:
    """Start scheduler and load all enabled jobs from DB."""
    global scheduler_instance
    scheduler_instance = _make_scheduler()
    scheduler_instance.start()
    _load_jobs_from_db()
    logger.info("Scheduler started")


def shutdown() -> None:
    global scheduler_instance
    if scheduler_instance and scheduler_instance.running:
        scheduler_instance.shutdown(wait=False)
        logger.info("Scheduler stopped")


def _load_jobs_from_db() -> None:
    from ..database import SessionLocal
    from ..models.job import Job, JobExecution

    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.is_enabled == True).all()  # noqa: E712
        for job in jobs:
            _register_job(job)

        # Back-fill next_run_at from APScheduler in a single commit
        for job in jobs:
            if scheduler_instance:
                aps_job = scheduler_instance.get_job(job.id)
                if aps_job and aps_job.next_run_time:
                    job.next_run_at = aps_job.next_run_time.isoformat()

        # Recover jobs stuck in running state (from a crash)
        stuck = db.query(Job).filter(Job.is_running == True).all()  # noqa: E712
        for job in stuck:
            job.is_running = False
            # Write a synthetic failed execution
            exec_record = JobExecution(
                job_id=job.id,
                started_at=job.last_run_at or datetime.now(timezone.utc).isoformat(),
                finished_at=datetime.now(timezone.utc).isoformat(),
                status="failed",
                stderr="Job was interrupted (unexpected shutdown)",
                triggered_by="scheduler",
            )
            db.add(exec_record)
            job.last_status = "failed"

        db.commit()
        logger.info(f"Loaded {len(jobs)} scheduled jobs, recovered {len(stuck)} stuck jobs")
    finally:
        db.close()


def _make_job_fn(job_id: str):
    """Return a closure that runs the job (fetches fresh DB state each time)."""
    def _run():
        from ..database import SessionLocal
        from ..models.job import Job
        from . import executor

        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if job is None or not job.is_enabled:
                return
            if job.is_running and not job.allow_concurrent:
                logger.info(f"Job '{job.name}' skipped: already running")
                return
            executor.run_job(job, db, triggered_by="scheduler")
        except Exception:
            logger.exception(f"Unhandled error in job fn for job_id={job_id}")
        finally:
            db.close()

    return _run


def _register_job(job) -> None:
    if scheduler_instance is None:
        return
    try:
        trigger = CronTrigger.from_crontab(job.cron_expression)
        max_instances = 10 if job.allow_concurrent else 1
        scheduler_instance.add_job(
            _make_job_fn(job.id),
            trigger=trigger,
            id=job.id,
            replace_existing=True,
            max_instances=max_instances,
        )
    except Exception as exc:
        logger.error(f"Failed to register job '{job.name}': {exc}")


def _update_next_run(job_id: str) -> None:
    if scheduler_instance is None:
        return
    from ..database import SessionLocal
    from ..models.job import Job

    aps_job = scheduler_instance.get_job(job_id)
    if aps_job is None:
        return
    next_run = aps_job.next_run_time
    if next_run:
        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if job:
                job.next_run_at = next_run.isoformat()
                db.commit()
        finally:
            db.close()


def add_job(job) -> None:
    _register_job(job)


def remove_job(job_id: str) -> None:
    if scheduler_instance and scheduler_instance.get_job(job_id):
        scheduler_instance.remove_job(job_id)


def pause_job(job_id: str) -> None:
    if scheduler_instance and scheduler_instance.get_job(job_id):
        scheduler_instance.pause_job(job_id)


def resume_job(job_id: str) -> None:
    if scheduler_instance and scheduler_instance.get_job(job_id):
        scheduler_instance.resume_job(job_id)
        _update_next_run(job_id)


def trigger_now(job_id: str) -> None:
    """Fire a job immediately as a one-shot date trigger."""
    if scheduler_instance is None:
        return
    from ..database import SessionLocal
    from ..models.job import Job
    from . import executor

    def _run_now():
        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if job:
                executor.run_job(job, db, triggered_by="manual")
        finally:
            db.close()

    scheduler_instance.add_job(
        _run_now,
        trigger="date",
        run_date=datetime.now(timezone.utc),
        id=f"manual_{job_id}_{datetime.now(timezone.utc).timestamp()}",
        replace_existing=False,
    )


def get_status() -> dict:
    if scheduler_instance is None:
        return {"running": False, "jobs": 0}
    return {
        "running": scheduler_instance.running,
        "jobs": len(scheduler_instance.get_jobs()),
    }
