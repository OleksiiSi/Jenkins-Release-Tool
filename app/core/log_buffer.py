from datetime import datetime
from threading import Lock

from core.models import LogEntry, LogLevel


class LogBuffer:
    def __init__(self):
        self._lock = Lock()
        self._entries: list[LogEntry] = []

    def append(self, message: str, level: LogLevel) -> None:
        with self._lock:
            self._entries.append(LogEntry(logged_at=datetime.now(), message=message, level=level))

    def pull_new_logs(self) -> list[LogEntry]:
        with self._lock:
            new_entries = self._entries
            self._entries = []

            return new_entries

    def clear_before_new_run(self) -> None:
        with self._lock:
            self._entries = []
