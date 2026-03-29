import os
import platform
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    db_path: str = "./data/cron_scheduler.db"
    log_level: str = "INFO"
    log_retention_days: int = 30
    max_concurrent_jobs: int = 10
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8000"
    upload_dir: str = "./data/job_files"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_windows(self) -> bool:
        return platform.system() == "Windows"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"


settings = Settings()
