import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from questlog.database import init_db
from questlog.routers import events, metrics, odoo, quests
from questlog.services.poller import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    events.set_event_loop(asyncio.get_running_loop())
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="QuestLog", lifespan=lifespan)

app.include_router(quests.router)
app.include_router(metrics.router)
app.include_router(odoo.router)
app.include_router(events.router)

app.mount("/static", StaticFiles(directory="questlog/static"), name="static")


@app.get("/")
def health():
    return {"app": "QuestLog", "status": "ok"}
