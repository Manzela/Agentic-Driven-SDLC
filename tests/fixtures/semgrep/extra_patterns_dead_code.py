"""Fixture: patterns the red-team found the first rule pass MISSED (F1-F4 fix-locks).

Non-standard router names, bare job decorators, first-arg callback registration, and
chained .weeks scheduler calls — all real-world wiring shapes the initial rules dropped.
"""

from fastapi import APIRouter
import schedule

api = APIRouter()
users_router = APIRouter()


# F1: non-standard app/router variable names (not 'app'/'router')
@api.get("/things")
def api_handler():
    return {"ok": True}


@users_router.post("/users")
def user_create(payload):
    return payload


# F2: bare job decorator from a non-Celery import (no dotted prefix)
from somejoblib import job


@job
def bare_job_fn():
    do_work()


# F3: callback as the FIRST positional argument (blinker / aiohttp style)
class Bus:
    def on(self, *a):
        pass


bus = Bus()


def first_arg_cb(event):
    handle(event)


bus.on(first_arg_cb, "event")


# F4: chained .weeks.do(...) scheduler registration
def weekly_job():
    rollup()


schedule.every(1).weeks.do(weekly_job)
