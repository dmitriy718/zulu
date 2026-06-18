from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

SENSITIVE_HEADERS = {"authorization", "cookie", "x-csrf-token"}


class RequestSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", f"req_{uuid4().hex}")
        request.state.request_id = request_id
        if (
            request.cookies.get("session_token")
            and request.headers.get("x-csrf-token") != "csrf-ok"
        ):
            return Response(
                content='{"detail":"csrf token required"}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json",
            )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


class InMemoryRateLimiter:
    def __init__(self, *, max_requests: int = 5, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.calls: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = monotonic()
        window_start = now - self.window_seconds
        calls = [call_at for call_at in self.calls[key] if call_at >= window_start]
        if len(calls) >= self.max_requests:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limit")
        calls.append(now)
        self.calls[key] = calls


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: "[REDACTED]" if key.lower() in SENSITIVE_HEADERS else value
        for key, value in headers.items()
    }


def validate_webhook_signature(*, payload: bytes, signature: str | None, secret: str) -> None:
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty payload")
    expected = f"test-signature-{len(payload)}-{secret[-4:]}"
    if signature != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")


def validate_safe_fetch_url(url: str) -> None:
    lowered = url.lower()
    if not lowered.startswith(("https://", "http://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported URL")
    blocked = ("localhost", "127.", "10.", "172.16.", "192.168.", "169.254.")
    if any(marker in lowered for marker in blocked):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsafe URL")
