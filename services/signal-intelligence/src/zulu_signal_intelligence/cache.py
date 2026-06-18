from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ProviderCacheKey:
    tenant_id: str
    provider_name: str
    operation: str
    instrument: str

    @property
    def value(self) -> str:
        return ":".join(
            (
                self.tenant_id,
                self.provider_name,
                self.operation,
                self.instrument.upper(),
            )
        )


@dataclass(frozen=True)
class CachedProviderValue[T]:
    value: T
    expires_at: datetime


class ProviderResponseCache:
    def __init__(self, *, ttl: timedelta = timedelta(seconds=15)) -> None:
        self.ttl = ttl
        self._values: dict[str, CachedProviderValue[object]] = {}

    def get(self, key: ProviderCacheKey, *, now: datetime) -> object | None:
        cached = self._values.get(key.value)
        if cached is None:
            return None
        if cached.expires_at <= now:
            self._values.pop(key.value, None)
            return None
        return cached.value

    def set(self, key: ProviderCacheKey, value: object, *, now: datetime) -> None:
        self._values[key.value] = CachedProviderValue(value=value, expires_at=now + self.ttl)

    def invalidate(self, key: ProviderCacheKey) -> None:
        self._values.pop(key.value, None)
