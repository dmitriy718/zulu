from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Protocol

from fastapi import Depends, Header, HTTPException, Request, status


class UserRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    OPERATOR = "operator"
    SUPPORT_READONLY = "support-readonly"


@dataclass(frozen=True)
class UserSession:
    tenant_id: str
    user_id: str
    role: UserRole
    token_id: str


class AuthProvider(Protocol):
    def authenticate(self, authorization_header: str | None) -> UserSession | None: ...


class FixtureAuthProvider:
    def __init__(self) -> None:
        self.sessions = {
            "token-owner": UserSession("tenant_1", "user_owner", UserRole.OWNER, "token-owner"),
            "token-admin": UserSession("tenant_1", "user_admin", UserRole.ADMIN, "token-admin"),
            "token-trader": UserSession("tenant_1", "user_trader", UserRole.TRADER, "token-trader"),
            "token-viewer": UserSession("tenant_1", "user_viewer", UserRole.VIEWER, "token-viewer"),
            "token-operator": UserSession(
                "tenant_1", "user_operator", UserRole.OPERATOR, "token-operator"
            ),
            "token-support": UserSession(
                "tenant_1", "user_support", UserRole.SUPPORT_READONLY, "token-support"
            ),
            "token-other": UserSession("tenant_2", "user_other", UserRole.OWNER, "token-other"),
        }

    def authenticate(self, authorization_header: str | None) -> UserSession | None:
        if authorization_header is None:
            return None
        scheme, _, token = authorization_header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        return self.sessions.get(token)


def get_auth_provider(request: Request) -> AuthProvider:
    provider = getattr(request.app.state, "auth_provider", None)
    if provider is None:
        provider = FixtureAuthProvider()
        request.app.state.auth_provider = provider
    return provider


def current_session(
    authorization: Annotated[str | None, Header()] = None,
    provider: AuthProvider = Depends(get_auth_provider),
) -> UserSession:
    session = provider.authenticate(authorization)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )
    return session


def require_tenant_access(tenant_id: str, session: UserSession) -> None:
    if session.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")


def require_role(session: UserSession, allowed_roles: set[UserRole]) -> None:
    if session.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")


def redact_token(token_id: str) -> str:
    if len(token_id) <= 4:
        return "[REDACTED]"
    return f"{token_id[:4]}...[REDACTED]"
