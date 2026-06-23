"""Fixture: decorator-routed handlers that are dead (never invoked from real paths)."""

from fastapi import FastAPI, APIRouter
from celery import Celery

app = FastAPI()
router = APIRouter()
celery_app = Celery()


# Dead handler: decorator-marked but never called
@app.get("/unused")
def unused_handler(request):
    return {"status": "never reached"}


# Dead callback: registered callback pattern but never invoked
@app.on_event("startup")
def dead_startup_hook():
    pass


# Dead Celery task: @celery.task but never invoked
@celery_app.task
def dead_async_job(data):
    process(data)


# Dead scheduled task: cron-style registration
@app.on_event("on_tick")
def scheduled_dead_task():
    cleanup()


# "Reachable" handler: invoked from __main__. Semgrep STILL flags it (it sees only
# the decorator, not reachability) — an accepted advisory FP under union-of-concerns;
# the AST checker, not Semgrep, decides reachability.
@app.get("/active")
def active_handler(request):
    return {"status": "ok"}


if __name__ == "__main__":
    active_handler(None)
