"""Threading."""

import sys
import sysconfig
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from multiprocessing import Manager
from typing import override

HASH_ITERATIONS_COUNT = 10000
MAX_CONCURRENT_WORKERS = 20


class PipelineError(Exception): ...


class Pipeline:
    """Pipeline class."""

    def __init__(self) -> None:
        self.results: dict[str, str] = {}

    def fetcher(self, task_id: str) -> str:
        """Fetch the data."""
        return f"{task_id}-{datetime.now(UTC).date()}"

    def processor(self, string: str) -> str:
        """Process string hashing."""
        for _ in range(HASH_ITERATIONS_COUNT):
            string = sha256(string.encode()).hexdigest()
        return string

    def storer(self, task_id: str, result: str) -> None:
        """Store the result."""
        self.results[task_id] = result

    def worker(self, task_id: str) -> str:
        """Worker function."""
        data = self.fetcher(task_id)
        result = self.processor(data)
        self.storer(task_id, result)
        return result

    def run(self, task_ids: list[str]) -> dict[str, str]:
        """Run the pipeline."""
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
            futures = [executor.submit(self.worker, task_id) for task_id in task_ids]
            for future in futures:
                _ = future.result()
        return self.results


from threading import Lock


class SafePipeline(Pipeline):
    """Thread-safe Pipeline."""

    def __init__(self) -> None:
        super().__init__()
        self._lock = Lock()

    def storer(self, task_id: str, result: str) -> None:
        """Store the result in a thread-safe manner."""
        with self._lock:
            self.results[task_id] = result


def is_gil_disabled() -> bool:
    """Check if GIL is disabled."""
    return (
        sysconfig.get_config_var("Py_GIL_DISABLED") == 1 and not sys._is_gil_enabled()
    )


class AdaptivePipeline(Pipeline):
    """Adaptive Pipeline."""

    def __init__(self) -> None:
        super().__init__()
        self._is_gil_disabled: bool = is_gil_disabled()
        if self._is_gil_disabled:
            self.results = Manager().dict()

    def get_executor(
        self,
    ) -> ThreadPoolExecutor | ProcessPoolExecutor:
        """Get the appropriate executor based on GIL status."""
        if self._is_gil_disabled:
            return ProcessPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS)
        return ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS)

    @override
    def processor(self, string: str) -> str:
        return super().processor(string)


if __name__ == "__main__":
    from datetime import datetime

    pipeline = Pipeline()
    task_ids = [f"task-{i}" for i in range(10)] + [ThreadPoolExecutor()]

    print(pipeline.run(task_ids))
