from abc import ABC, abstractmethod

from core import cache_manager


class BaseClient(ABC):
    _CACHE_KEY: str

    last_check_was_cached: bool = False

    @property
    @abstractmethod
    def _current_value(self) -> str:
        pass

    @abstractmethod
    def _test_connection(self) -> bool:
        pass

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
