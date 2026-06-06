import asyncio

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from questlog.database import init_db
from questlog.routers import events, metrics, odoo, quests
from questlog.services.poller import start_scheduler, stop_scheduler

app = FastAPI(title="QuestLog")

app.include_router(quests.router)
app.include_router(metrics.router)
app.include_router(odoo.router)
app.include_router(events.router)

app.mount("/static", StaticFiles(directory="questlog/static"), name="static")


@app.get("/")
def health():
    return {"app": "QuestLog", "status": "ok"}


@app.on_event("startup")
async def on_startup():
    init_db()
    events.set_event_loop(asyncio.get_running_loop())
    start_scheduler()


@app.on_event("shutdown")
async def on_shutdown():
    stop_scheduler()
