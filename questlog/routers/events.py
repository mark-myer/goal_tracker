import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()
_subscribers: set[asyncio.Queue] = set()
_main_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def broadcast_event(payload: dict) -> None:
    if not _main_loop:
        return
    for queue in list(_subscribers):
        _main_loop.call_soon_threadsafe(queue.put_nowait, payload)


async def _stream() -> AsyncGenerator[str, None]:
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.add(queue)
    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=15)
                yield f"event: metric_update\ndata: {json.dumps(payload)}\n\n"
            except TimeoutError:
                yield ": keepalive\n\n"
    finally:
        _subscribers.discard(queue)


@router.get("/events")
async def events():
    return StreamingResponse(_stream(), media_type="text/event-stream")
