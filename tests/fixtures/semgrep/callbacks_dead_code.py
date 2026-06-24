"""Fixture: registered-but-uninvoked callbacks."""

import asyncio
import queue

# Callback registered to an event emitter but never triggered
class EventEmitter:
    def __init__(self):
        self.handlers = []

    def on(self, event, fn):
        self.handlers.append(fn)

    def emit(self, event, *args):
        for fn in self.handlers:
            fn(*args)


# This callback is registered but never triggered (dead)
def dead_callback(event):
    handle_event(event)


emitter = EventEmitter()
emitter.on("data", dead_callback)


# This callback IS called directly from module level (reachable)
def active_callback(event):
    print(event)


active_callback("test")
