"""RQ worker entrypoint for the signal-classification queue.

Run with: python worker.py
Needs a running Redis server (REDIS_URL in .env) and a migrated Postgres
database — this is real background-job infrastructure, not something
unit tests spin up.
"""

from rq import Worker

from app.services.signal_queue import SIGNAL_QUEUE_NAME, get_sync_redis_connection

if __name__ == "__main__":
    connection = get_sync_redis_connection()
    worker = Worker([SIGNAL_QUEUE_NAME], connection=connection)
    worker.work()
