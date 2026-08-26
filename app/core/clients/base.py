from abc import ABC, abstractmethod

from core import cache_manager


class BaseClient(ABC):
    """Template for a client whose connectivity can be checked and cached.

    Subclasses provide `_current_value` (the config that, if changed, forces
    a fresh check) and `_test_connection` (the actual network probe).
    """

    _CACHE_KEY: str

    # Set on every check_connection() call - True if the cached "ok" result
    # was reused, False if _test_connection() actually hit the network. Lets
    # callers log *why* nothing happened on a passing check, not just that it
    # passed.
    last_check_was_cached: bool = False

    @property
    @abstractmethod
    def _current_value(self) -> str:
        """The client's current connection config (e.g. base_url+token, or a
        webhook URL) - whatever changing it should force a fresh check."""

    @abstractmethod
    def _test_connection(self) -> bool:
        """Perform the actual network check. True if it succeeded."""

    def check_connection(self) -> bool:
        fingerprint = self._current_value
        cache_entry = cache_manager.get_cache_entry(self._CACHE_KEY)

        if (
            cache_entry
            and cache_manager.matches_cached_value(cache_entry, fingerprint)
            and cache_entry.get("is_valid", False)
        ):
            self.last_check_was_cached = True
            return True

        self.last_check_was_cached = False
        is_valid = self._test_connection()
        cache_manager.record_result(self._CACHE_KEY, fingerprint, is_valid)

        return is_valid
