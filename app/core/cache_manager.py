import hashlib
import json
from datetime import datetime

from core.config import CONNECTION_CHECKS_CACHE_PATH


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_cache() -> dict:
    if not CONNECTION_CHECKS_CACHE_PATH.exists():
        return {}

    try:
        return json.loads(CONNECTION_CHECKS_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache_key: str, cache_value: dict) -> None:
    cache = _load_cache()
    cache[cache_key] = cache_value

    CONNECTION_CHECKS_CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def get_cache_entry(cache_key: str) -> dict | None:
    return _load_cache().get(cache_key, None)


def matches_cached_value(cache_entry: dict, value: str) -> bool:
    return cache_entry.get("hash", None) == _hash(value)


def record_result(cache_key: str, value: str, is_valid: bool) -> None:
    _save_cache(cache_key, {"hash": _hash(value), "is_valid": is_valid, "checked_at": datetime.now().isoformat()})
