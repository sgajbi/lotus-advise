from __future__ import annotations

import time
from collections import OrderedDict
from threading import RLock
from typing import Callable, Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TimedCache(Generic[K, V]):
    def __init__(
        self,
        *,
        clone_value: Callable[[V], V],
        ttl_seconds: Callable[[], float],
        max_size: Callable[[], int],
    ) -> None:
        self._clone_value = clone_value
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        self._lock = RLock()
        self._values: OrderedDict[K, tuple[float, V]] = OrderedDict()

    def get(self, key: K) -> V | None:
        now = time.monotonic()
        with self._lock:
            cached_entry = self._values.get(key)
            if cached_entry is None:
                return None
            expires_at, value = cached_entry
            if expires_at < now:
                self._values.pop(key, None)
                return None
            self._values.move_to_end(key)
            return self._clone_value(value)

    def set(self, key: K, value: V) -> V:
        with self._lock:
            self._values[key] = (
                time.monotonic() + self._ttl_seconds(),
                self._clone_value(value),
            )
            self._values.move_to_end(key)
            while len(self._values) > self._max_size():
                self._values.popitem(last=False)
        return self._clone_value(value)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()
