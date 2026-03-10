"""SSE event broadcaster — bridges scheduler threads to async SSE queues."""
import asyncio
import json
import logging
from typing import Set

logger = logging.getLogger(__name__)

_queues: Set[asyncio.Queue] = set()
_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _queues.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _queues.discard(q)


def broadcast(event_type: str, payload: dict) -> None:
    """Called from scheduler background threads — thread-safe."""
    if not _queues or _loop is None:
        return
    message = json.dumps({"type": event_type, "data": payload})
    for q in list(_queues):
        try:
            _loop.call_soon_threadsafe(q.put_nowait, message)
        except asyncio.QueueFull:
            logger.warning("SSE queue full, dropping event for a client")
        except Exception as exc:
            logger.warning(f"SSE broadcast error: {exc}")
