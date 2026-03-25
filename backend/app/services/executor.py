"""Cross-platform subprocess runner for scheduled jobs."""
import json
import logging
import os
import platform
import signal
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy.orm import Session

from ..models.job import Job, JobExecution
from . import notifier

logger = logging.getLogger(__name__)

MAX_OUTPUT_BYTES = 1 * 1024 * 1024  # 1 MB per stream

_running_procs: Dict[str, subprocess.Popen] = {}  # execution_id -> Popen


def _build_command(job: Job) -> List[str]:
    """Build the platform-appropriate command list."""
    cmd = job.command
    shell = job.shell_type

    if platform.system() == "Windows":
        if shell == "powershell":
            return ["powershell.exe", "-NonInteractive", "-Command", cmd]
        # auto or cmd
        return ["cmd.exe", "/c", cmd]
    else:
        if shell == "sh":
            return ["sh", "-c", cmd]
        # auto or bash
        bash = _find_bash()
        return [bash, "-c", cmd]


def _find_bash() -> str:
    for candidate in ["/bin/bash", "/usr/bin/bash", "/usr/local/bin/bash"]:
        if os.path.isfile(candidate):
            return candidate
    return "bash"


def _truncate(text: str, limit: int = MAX_OUTPUT_BYTES) -> str:
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return text
    truncated = encoded[-limit:]
    return "[...output truncated...]\n" + truncated.decode("utf-8", errors="replace")


def run_job(job: Job, db: Session, triggered_by: str = "scheduler", retry_number: int = 0) -> str:
    """
    Execute a job synchronously (called from a scheduler background thread).
    Returns the execution id.
    """
    exec_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    # Create execution record
    execution = JobExecution(
        id=exec_id,
        job_id=job.id,
        started_at=started_at,
        status="running",
        triggered_by=triggered_by,
        retry_number=retry_number,
    )
    db.add(execution)

    # Mark job as running
    job.is_running = True
    job.last_run_at = started_at
    db.commit()

    notifier.broadcast("execution_started", {
        "job_id": job.id,
        "execution_id": exec_id,
        "job_name": job.name,
        "triggered_by": triggered_by,
    })

    try:
        cmd_args = _build_command(job)
        env_vars = {}
        if job.environment_vars:
            try:
                env_vars = json.loads(job.environment_vars)
            except Exception:
                pass

        merged_env = {**os.environ, **env_vars}
        cwd = job.working_directory or None

        proc = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=merged_env,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        execution.pid = proc.pid
        db.commit()
        _running_procs[exec_id] = proc

        timeout = job.timeout_seconds if job.timeout_seconds and job.timeout_seconds > 0 else None

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            exit_code = proc.returncode
            status = "success" if exit_code == 0 else "failed"
        except subprocess.TimeoutExpired:
            _kill_proc(proc)
            stdout, stderr = proc.communicate()
            exit_code = None
            status = "timeout"

    except Exception as exc:
        logger.exception(f"Job {job.id} executor error: {exc}")
        stdout = ""
        stderr = str(exc)
        exit_code = -1
        status = "failed"
    finally:
        _running_procs.pop(exec_id, None)

    finished_at = datetime.now(timezone.utc).isoformat()
    start_dt = datetime.fromisoformat(started_at)
    finish_dt = datetime.fromisoformat(finished_at)
    duration_ms = int((finish_dt - start_dt).total_seconds() * 1000)

    execution.finished_at = finished_at
    execution.duration_ms = duration_ms
    execution.exit_code = exit_code
    execution.status = status
    execution.stdout = _truncate(stdout or "")
    execution.stderr = _truncate(stderr or "")

    job.is_running = False
    job.last_status = status

    db.commit()

    notifier.broadcast("execution_finished", {
        "job_id": job.id,
        "execution_id": exec_id,
        "job_name": job.name,
        "status": status,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
    })

    # Handle retries
    if status == "failed" and retry_number < job.max_retries:
        _schedule_retry(job, db, retry_number + 1)

    logger.info(f"Job '{job.name}' [{exec_id}] finished: {status} (exit={exit_code}, {duration_ms}ms)")
    return exec_id


def kill_execution(exec_id: str) -> bool:
    """Kill a running execution by its ID. Returns True if killed."""
    proc = _running_procs.get(exec_id)
    if proc is None:
        return False
    _kill_proc(proc)
    return True


def _kill_proc(proc: subprocess.Popen) -> None:
    try:
        if platform.system() == "Windows":
            proc.kill()
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _schedule_retry(job: Job, db: Session, retry_number: int) -> None:
    """Schedule a one-shot retry via APScheduler after the retry delay."""
    from datetime import timedelta
    from . import scheduler as scheduler_svc

    run_at = datetime.now(timezone.utc) + timedelta(seconds=job.retry_delay_seconds)
    logger.info(f"Scheduling retry #{retry_number} for job '{job.name}' at {run_at.isoformat()}")

    # Capture job_id to avoid session issues in the retry thread
    job_id = job.id

    def retry_fn():
        from ..database import SessionLocal
        retry_db = SessionLocal()
        try:
            retry_job = retry_db.get(Job, job_id)
            if retry_job and retry_job.is_enabled:
                run_job(retry_job, retry_db, triggered_by="retry", retry_number=retry_number)
        finally:
            retry_db.close()

    scheduler_svc.scheduler_instance.add_job(
        retry_fn,
        trigger="date",
        run_date=run_at,
        id=f"retry_{job_id}_{retry_number}",
        replace_existing=True,
    )
