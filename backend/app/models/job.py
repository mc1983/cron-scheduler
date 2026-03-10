import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from ..database import Base


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_uuid() -> str:
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    command = Column(Text, nullable=False)
    cron_expression = Column(String, nullable=False)
    working_directory = Column(String, default="")
    environment_vars = Column(Text, default="{}")   # JSON string
    shell_type = Column(String, default="auto")     # auto|cmd|powershell|bash|sh
    timeout_seconds = Column(Integer, default=3600)
    max_retries = Column(Integer, default=0)
    retry_delay_seconds = Column(Integer, default=60)
    allow_concurrent = Column(Boolean, default=False)
    is_enabled = Column(Boolean, default=True)
    is_running = Column(Boolean, default=False)
    last_run_at = Column(String, default=None)
    next_run_at = Column(String, default=None)
    last_status = Column(String, default=None)      # success|failed|timeout|killed
    created_at = Column(String, default=now_utc)
    updated_at = Column(String, default=now_utc, onupdate=now_utc)

    executions = relationship(
        "JobExecution", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Job id={self.id} name={self.name!r} cron={self.cron_expression!r}>"


class JobExecution(Base):
    __tablename__ = "job_executions"

    id = Column(String, primary_key=True, default=new_uuid)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(String, nullable=False)
    finished_at = Column(String, default=None)
    duration_ms = Column(Integer, default=None)
    exit_code = Column(Integer, default=None)
    status = Column(String, nullable=False)         # running|success|failed|timeout|killed
    stdout = Column(Text, default="")
    stderr = Column(Text, default="")
    triggered_by = Column(String, default="scheduler")  # scheduler|manual|retry
    retry_number = Column(Integer, default=0)
    pid = Column(Integer, default=None)

    job = relationship("Job", back_populates="executions")

    __table_args__ = (
        Index("idx_executions_job_id", "job_id"),
        Index("idx_executions_started_at", "started_at"),
        Index("idx_executions_status", "status"),
    )

    def __repr__(self):
        return f"<JobExecution id={self.id} job_id={self.job_id} status={self.status!r}>"
