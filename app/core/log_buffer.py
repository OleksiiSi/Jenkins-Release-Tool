from datetime import datetime
from threading import Lock

from core.models import LogEntry, LogLevel


class LogBuffer:
    """Thread-safe store of one run's not-yet-polled log lines.

    One instance lives for the app's lifetime. `pull_new_logs()` drains the
    buffer - each entry is returned exactly once, to whichever caller polls
    next, so this is only correct with exactly one poller (this app's single
    webview window); a second caller would silently steal lines the first
    caller never saw. `clear_before_new_run()` exists separately for
    discarding leftover unpolled entries from a previous run when a new one
    starts.
    """

    def __init__(self):
        self._lock = Lock()
        self._entries: list[LogEntry] = []

    def append(self, message: str, level: LogLevel) -> None:
        with self._lock:
            self._entries.append(LogEntry(logged_at=datetime.now(), message=message, level=level))

    def pull_new_logs(self) -> list[LogEntry]:
        """Every entry appended since the last call to this method, then
        empties the buffer - each entry is returned exactly once."""
        with self._lock:
            new_entries = self._entries
            self._entries = []

            return new_entries

    def clear_before_new_run(self) -> None:
        with self._lock:
            self._entries = []
