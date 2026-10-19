"""Only enqueue_raw_signal is unit tested here — everything past that
point (a real RQ worker picking up the job, opening a real database
session) needs a real Redis server and a real Postgres database, neither
of which exist in this sandbox. See PROJECT_GUIDE.md for how to verify
that part yourself by actually running worker.py.
"""

from uuid import uuid4

from app.schemas.signal import RawSignalItem
from app.services.signal_queue import classify_and_store_job, enqueue_raw_signal


class FakeQueue:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def enqueue(self, func, *args) -> None:  # noqa: ANN001
        self.calls.append((func, args))


def test_enqueue_raw_signal_pushes_the_right_job_and_arguments() -> None:
    queue = FakeQueue()
    raw_item = RawSignalItem(title="Acme raises funding", link="https://example.com/x")
    mission_id = uuid4()

    enqueue_raw_signal(queue, raw_item, mission_id)  # type: ignore[arg-type]

    assert len(queue.calls) == 1
    func, args = queue.calls[0]
    assert func is classify_and_store_job
    raw_item_data, mission_id_str = args
    assert raw_item_data["title"] == "Acme raises funding"
    assert mission_id_str == str(mission_id)
