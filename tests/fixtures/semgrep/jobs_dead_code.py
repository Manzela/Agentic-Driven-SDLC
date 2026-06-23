"""Fixture: job/scheduled-task registration patterns (the 8.2 fourth category)."""

from typing import Callable
import schedule

# APScheduler-style job registration (dead)
def schedule_dead_job():
    """Job registered but never executed in tests."""
    log_metrics()


schedule.every(10).seconds.do(schedule_dead_job)


# Queue consumer registration (dead) — e.g. a RabbitMQ consumer registered but never called
class QueueConsumer:
    def register_handler(self, queue_name: str, handler: Callable):
        self.handlers[queue_name] = handler


consumer = QueueConsumer()


def dead_queue_handler(msg):
    """Registered to queue but never invoked."""
    process_message(msg)


consumer.register_handler("input_queue", dead_queue_handler)


# Entry point style (dead)
ENTRY_POINTS = {
    "data_processor": dead_queue_handler,
    "scheduler": schedule_dead_job,
}
