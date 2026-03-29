import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ..config import settings
from ..database import get_db
from ..models.job import Job
from ..schemas.job import JobCreate, JobUpdate, JobResponse, JobListResponse
from ..services import scheduler as scheduler_svc

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_to_response(job: Job) -> JobResponse:
    return JobResponse.from_orm_model(job)


def _get_job_or_404(job_id: str, db: Session) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    return job


def _sync_next_run(job: Job, db: Session) -> None:
    """Read next_run_at from APScheduler and persist to DB."""
    aps = scheduler_svc.scheduler_instance
    if aps is None:
        return
    aps_job = aps.get_job(job.id)
    if aps_job and aps_job.next_run_time:
        job.next_run_at = aps_job.next_run_time.isoformat()
        db.commit()


@router.get("", response_model=JobListResponse)
def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_enabled: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Job)
    if is_enabled is not None:
        q = q.filter(Job.is_enabled == is_enabled)
    if search:
        q = q.filter(Job.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return JobListResponse(
        items=[_job_to_response(j) for j in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=JobResponse, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    job = Job(
        name=payload.name,
        description=payload.description,
        command=payload.command,
        cron_expression=payload.cron_expression,
        working_directory=payload.working_directory,
        environment_vars=json.dumps(payload.environment_vars),
        shell_type=payload.shell_type,
        timeout_seconds=payload.timeout_seconds,
        max_retries=payload.max_retries,
        retry_delay_seconds=payload.retry_delay_seconds,
        allow_concurrent=payload.allow_concurrent,
        is_enabled=payload.is_enabled,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if job.is_enabled:
        scheduler_svc.add_job(job)
        _sync_next_run(job, db)

    return _job_to_response(job)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    return _job_to_response(_get_job_or_404(job_id, db))


@router.put("/{job_id}", response_model=JobResponse)
def update_job(job_id: str, payload: JobUpdate, db: Session = Depends(get_db)):
    job = _get_job_or_404(job_id, db)
    update_data = payload.model_dump(exclude_unset=True)

    if "environment_vars" in update_data:
        update_data["environment_vars"] = json.dumps(update_data["environment_vars"])

    for field, value in update_data.items():
        setattr(job, field, value)

    job.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(job)

    # Re-register with scheduler
    scheduler_svc.remove_job(job.id)
    if job.is_enabled:
        scheduler_svc.add_job(job)
        _sync_next_run(job, db)

    return _job_to_response(job)


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(job_id, db)
    scheduler_svc.remove_job(job.id)
    if job.package_name:
        job_dir = os.path.abspath(os.path.join(settings.upload_dir, job_id))
        shutil.rmtree(job_dir, ignore_errors=True)
    db.delete(job)
    db.commit()


def _do_extract(contents: bytes, job_dir: str) -> None:
    """Extract zip bytes into job_dir. Runs in a thread-pool worker."""
    if os.path.exists(job_dir):
        shutil.rmtree(job_dir)
    os.makedirs(job_dir)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        with zipfile.ZipFile(tmp_path, "r") as zf:
            zf.extractall(job_dir)
    except:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/{job_id}/upload", response_model=JobResponse)
def upload_job_package(
    job_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    job = _get_job_or_404(job_id, db)

    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")

    job_dir = os.path.abspath(os.path.join(settings.upload_dir, job_id))

    # file.file is the underlying SpooledTemporaryFile — seek/read synchronously.
    file.file.seek(0)
    contents = file.file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty — python-multipart may not be installed")

    logger.info(f"Uploading package for job {job_id}: {file.filename!r} ({len(contents)} bytes) → {job_dir}")

    try:
        _do_extract(contents, job_dir)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid or corrupt ZIP file")
    except Exception as exc:
        logger.exception(f"ZIP extraction failed for job {job_id}")
        raise HTTPException(status_code=500, detail=f"Failed to extract ZIP: {exc}")

    job.working_directory = job_dir
    job.package_name = file.filename
    job.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(job)

    logger.info(f"Job {job_id} working_directory set to {job_dir!r}")

    # Re-register so the updated working_directory takes effect immediately
    scheduler_svc.remove_job(job.id)
    if job.is_enabled:
        scheduler_svc.add_job(job)
        _sync_next_run(job, db)

    return _job_to_response(job)


@router.post("/{job_id}/run", response_model=dict)
def run_job_now(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(job_id, db)
    if not job.is_enabled:
        raise HTTPException(status_code=400, detail="Job is disabled")
    scheduler_svc.trigger_now(job.id)
    return {"message": "Job triggered", "job_id": job_id}


@router.post("/{job_id}/pause", response_model=JobResponse)
def pause_job(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(job_id, db)
    job.is_enabled = False
    job.next_run_at = None
    job.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    scheduler_svc.remove_job(job.id)
    db.refresh(job)
    return _job_to_response(job)


@router.post("/{job_id}/resume", response_model=JobResponse)
def resume_job(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(job_id, db)
    job.is_enabled = True
    job.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(job)
    scheduler_svc.add_job(job)
    _sync_next_run(job, db)
    return _job_to_response(job)
