import asyncio
import logging
import logging.handlers
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .services import notifier
from .services import scheduler as scheduler_svc
from .routers import jobs, executions, system

# ── Logging setup ────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            "logs/scheduler.log", maxBytes=10 * 1024 * 1024, backupCount=5
        ),
    ],
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    os.makedirs(settings.upload_dir, exist_ok=True)
    notifier.set_event_loop(asyncio.get_event_loop())
    scheduler_svc.start()
    logger.info("Cron Scheduler service started")
    yield
    # Shutdown
    scheduler_svc.shutdown()
    logger.info("Cron Scheduler service stopped")


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Cron Scheduler API",
    description="Cross-platform job scheduler — create, monitor and manage batch job schedules",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import uuid
    error_id = str(uuid.uuid4())
    logger.exception(f"Unhandled error [{error_id}]: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_id": error_id},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(executions.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


# ── Static frontend (production build) ───────────────────────────────────────
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="static")
    logger.info(f"Serving frontend from {_frontend_dist}")
