from __future__ import annotations
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from croniter import croniter


class JobCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    command: str = Field(..., min_length=1)
    cron_expression: str = Field(..., description="Standard 5-field cron expression")
    working_directory: str = Field(default="")
    environment_vars: Dict[str, str] = Field(default_factory=dict)
    shell_type: str = Field(default="auto")
    timeout_seconds: int = Field(default=3600, ge=0)
    max_retries: int = Field(default=0, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=1)
    allow_concurrent: bool = Field(default=False)
    is_enabled: bool = Field(default=True)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: {v!r}")
        return v

    @field_validator("shell_type")
    @classmethod
    def validate_shell(cls, v: str) -> str:
        allowed = {"auto", "cmd", "powershell", "bash", "sh"}
        if v not in allowed:
            raise ValueError(f"shell_type must be one of {allowed}")
        return v


class JobUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    command: Optional[str] = Field(default=None, min_length=1)
    cron_expression: Optional[str] = None
    working_directory: Optional[str] = None
    environment_vars: Optional[Dict[str, str]] = None
    shell_type: Optional[str] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=0)
    max_retries: Optional[int] = Field(default=None, ge=0, le=10)
    retry_delay_seconds: Optional[int] = Field(default=None, ge=1)
    allow_concurrent: Optional[bool] = None
    is_enabled: Optional[bool] = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: {v!r}")
        return v

    @field_validator("shell_type")
    @classmethod
    def validate_shell(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"auto", "cmd", "powershell", "bash", "sh"}
            if v not in allowed:
                raise ValueError(f"shell_type must be one of {allowed}")
        return v


class JobResponse(BaseModel):
    id: str
    name: str
    description: str
    command: str
    cron_expression: str
    working_directory: str
    environment_vars: Dict[str, str]
    shell_type: str
    timeout_seconds: int
    max_retries: int
    retry_delay_seconds: int
    allow_concurrent: bool
    is_enabled: bool
    is_running: bool
    last_run_at: Optional[str]
    next_run_at: Optional[str]
    last_status: Optional[str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, job: Any) -> "JobResponse":
        import json
        data = {c.name: getattr(job, c.name) for c in job.__table__.columns}
        try:
            data["environment_vars"] = json.loads(data.get("environment_vars") or "{}")
        except Exception:
            data["environment_vars"] = {}
        return cls(**data)


class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
