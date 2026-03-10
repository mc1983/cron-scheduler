from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel


class ExecutionResponse(BaseModel):
    id: str
    job_id: str
    job_name: Optional[str] = None
    started_at: str
    finished_at: Optional[str]
    duration_ms: Optional[int]
    exit_code: Optional[int]
    status: str
    stdout: str
    stderr: str
    triggered_by: str
    retry_number: int
    pid: Optional[int]

    model_config = {"from_attributes": True}


class ExecutionListResponse(BaseModel):
    items: List[ExecutionResponse]
    total: int
    page: int
    page_size: int
