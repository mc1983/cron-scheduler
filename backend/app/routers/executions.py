from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.job import Job, JobExecution
from ..schemas.execution import ExecutionResponse, ExecutionListResponse
from ..services import executor as executor_svc

router = APIRouter(prefix="/executions", tags=["executions"])


def _exec_to_response(exc: JobExecution, job_name: Optional[str] = None) -> ExecutionResponse:
    return ExecutionResponse(
        id=exc.id,
        job_id=exc.job_id,
        job_name=job_name or (exc.job.name if exc.job else None),
        started_at=exc.started_at,
        finished_at=exc.finished_at,
        duration_ms=exc.duration_ms,
        exit_code=exc.exit_code,
        status=exc.status,
        stdout=exc.stdout or "",
        stderr=exc.stderr or "",
        triggered_by=exc.triggered_by or "scheduler",
        retry_number=exc.retry_number or 0,
        pid=exc.pid,
    )


@router.get("", response_model=ExecutionListResponse)
def list_executions(
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(JobExecution)
    if job_id:
        q = q.filter(JobExecution.job_id == job_id)
    if status:
        q = q.filter(JobExecution.status == status)
    if from_date:
        q = q.filter(JobExecution.started_at >= from_date)
    if to_date:
        q = q.filter(JobExecution.started_at <= to_date)

    total = q.count()
    items = q.order_by(JobExecution.started_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Eager load job names
    results = []
    for exc in items:
        job_name = exc.job.name if exc.job else None
        results.append(_exec_to_response(exc, job_name))

    return ExecutionListResponse(items=results, total=total, page=page, page_size=page_size)


@router.get("/{exec_id}", response_model=ExecutionResponse)
def get_execution(exec_id: str, db: Session = Depends(get_db)):
    exc = db.get(JobExecution, exec_id)
    if not exc:
        raise HTTPException(status_code=404, detail=f"Execution {exec_id!r} not found")
    return _exec_to_response(exc)


@router.delete("/{exec_id}", status_code=204)
def delete_execution(exec_id: str, db: Session = Depends(get_db)):
    exc = db.get(JobExecution, exec_id)
    if not exc:
        raise HTTPException(status_code=404, detail=f"Execution {exec_id!r} not found")
    db.delete(exc)
    db.commit()


@router.post("/{exec_id}/kill", response_model=dict)
def kill_execution(exec_id: str, db: Session = Depends(get_db)):
    exc = db.get(JobExecution, exec_id)
    if not exc:
        raise HTTPException(status_code=404, detail=f"Execution {exec_id!r} not found")
    if exc.status != "running":
        raise HTTPException(status_code=400, detail=f"Execution is not running (status={exc.status!r})")
    killed = executor_svc.kill_execution(exec_id)
    if not killed:
        raise HTTPException(status_code=400, detail="Process not found (may have already finished)")
    return {"message": "Kill signal sent", "execution_id": exec_id}
