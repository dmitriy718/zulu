from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import monotonic, sleep
from typing import ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")


class ProviderRateLimitError(RuntimeError):
    pass


class ProviderCircuitOpenError(RuntimeError):
    pass


class ProviderTimeoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.05
    backoff_multiplier: float = 2.0
    timeout_seconds: float = 2.0


class CircuitBreaker:
    def __init__(
        self, *, failure_threshold: int = 3, reset_after: timedelta = timedelta(seconds=30)
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_after = reset_after
        self._failure_count = 0
        self._opened_at: datetime | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        return datetime.now(UTC) - self._opened_at < self.reset_after

    def record_success(self) -> None:
        self._failure_count = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self._opened_at = datetime.now(UTC)


class ProviderExecutor:
    def __init__(
        self,
        *,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    def call(
        self,
        provider_name: str,
        operation: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        if self.circuit_breaker.is_open:
            raise ProviderCircuitOpenError(f"{provider_name} provider circuit is open")

        delay = self.retry_policy.base_delay_seconds
        last_error: Exception | None = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                started_at = monotonic()
                result = operation(*args, **kwargs)
                elapsed = monotonic() - started_at
                if elapsed > self.retry_policy.timeout_seconds:
                    raise ProviderTimeoutError(
                        f"{provider_name} provider operation exceeded timeout"
                    )
            except ProviderRateLimitError as exc:
                last_error = exc
                self.circuit_breaker.record_failure()
                if attempt == self.retry_policy.max_attempts:
                    break
                sleep(delay)
                delay *= self.retry_policy.backoff_multiplier
            except ProviderTimeoutError:
                self.circuit_breaker.record_failure()
                raise
            except Exception as exc:
                self.circuit_breaker.record_failure()
                raise exc
            else:
                self.circuit_breaker.record_success()
                return result

        if last_error is not None:
            raise last_error
        raise ProviderCircuitOpenError(f"{provider_name} provider call failed without a result")
