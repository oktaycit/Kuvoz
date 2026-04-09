"""Background task coordination helpers."""

from __future__ import annotations

import threading
import time


class BackgroundTaskManager:
    """Prevent overlapping long-running UI-triggered tasks."""

    def __init__(self, *, logger):
        self._logger = logger
        self._lock = threading.Lock()
        self._active_task = None
        self._start_time = 0

    def start_task(self, task_name):
        with self._lock:
            if self._active_task:
                if time.time() - self._start_time > 600:
                    self._logger.warning(
                        f"⚠️ Stale task detected: {self._active_task}. Forcing start of {task_name}"
                    )
                    self._active_task = task_name
                    self._start_time = time.time()
                    return True
                return False
            self._active_task = task_name
            self._start_time = time.time()
            return True

    def end_task(self):
        with self._lock:
            self._active_task = None
            self._start_time = 0

    @property
    def is_busy(self):
        return self._active_task is not None

    @property
    def current_task(self):
        return self._active_task
