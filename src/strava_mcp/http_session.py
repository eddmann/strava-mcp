"""HTTP mode session management - OAuth services, session storage, and request context."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlencode

import boto3  # type: ignore[reportMissingTypeStubs]
import httpx
from mcp.server.auth.provider import (
    AccessToken as OAuthAccessToken,
)
from mcp.server.auth.provider import (
    AuthorizationCode,
)
from mcp.server.auth.provider import (
    RefreshToken as OAuthRefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl, AnyUrl, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import TokenResponse

# Type aliases for OAuth provider
ProviderAccessToken = OAuthAccessToken
ProviderRefreshToken = OAuthRefreshToken

# Constants for HTTP mode session management
DEFAULT_STRAVA_SCOPES = [
    "profile:read_all",
    "activity:read_all",
    "activity:read",
    "profile:write",
]

DEFAULT_REGISTERED_CLIENTS = {
    "chatgpt": ["https://mcp.openai.com/v1/oauth/callback"],
}

SESSION_TTL = timedelta(hours=12)
TOKEN_REFRESH_SKEW = timedelta(minutes=2)
AUTHORIZATION_CODE_TTL_SECONDS = 300
DYNAMODB_DEFAULT_TTL_SECONDS = int(timedelta(days=10).total_seconds())
# ============================================================================


class StravaAppConfig(BaseSettings):
    """Strava API configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_measurement_preference: Literal["meters", "feet"] = "meters"
    route_export_path: str = "./exports"
    strava_oauth_scopes: str | None = None
    mcp_oauth_clients: str | None = None

    @model_validator(mode="after")
    def validate_credentials(self) -> StravaAppConfig:
        """Validate that required credentials are configured."""
        if not self.strava_client_id or self.strava_client_id == "your_client_id_here":
            raise ValueError("STRAVA_CLIENT_ID is not configured. Please set it in your .env file.")
        if not self.strava_client_secret or self.strava_client_secret == "your_client_secret_here":
            raise ValueError(
                "STRAVA_CLIENT_SECRET is not configured. Please set it in your .env file."
            )
        return self


def _parse_scopes(config: StravaAppConfig) -> list[str]:
    """Determine the scopes to request from Strava."""
    if config.strava_oauth_scopes:
        scopes = [scope.strip() for scope in config.strava_oauth_scopes.split(",") if scope.strip()]
        return scopes or DEFAULT_STRAVA_SCOPES
    return DEFAULT_STRAVA_SCOPES


def parse_registered_clients(config: StravaAppConfig) -> dict[str, list[str]]:
    """Parse MCP OAuth client configuration."""
    clients: dict[str, list[str]] = {}

    raw = config.mcp_oauth_clients
    if raw:
        for entry in raw.split(";"):
            entry = entry.strip()
            if not entry:
                continue
            if "=" not in entry:
                continue
            client_id, redirect_block = entry.split("=", 1)
            redirect_uris = [uri.strip() for uri in redirect_block.split(",") if uri.strip()]
            if redirect_uris:
                clients[client_id.strip()] = redirect_uris

    for client_id, redirect_uris in DEFAULT_REGISTERED_CLIENTS.items():
        clients.setdefault(client_id, redirect_uris)

    return clients


@dataclass
class StravaSession:
    """Per-user Strava credentials and metadata stored in memory."""

    session_id: str
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: list[str]
    created_at: datetime
    updated_at: datetime
    session_expires_at: datetime
    athlete_id: int | None = None
    athlete_name: str | None = None
    athlete: dict[str, Any] | None = None
    mcp_token: str | None = None
    oauth_refresh_token: str | None = None
    client_id: str | None = None
    resource: str | None = None

    def as_public_dict(self) -> dict[str, Any]:
        """Return a redacted view suitable for logging or diagnostics."""
        return {
            "session_id": self.session_id,
            "athlete_id": self.athlete_id,
            "athlete_name": self.athlete_name,
            "scopes": ",".join(self.scopes),
            "client_id": self.client_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "session_expires_at": self.session_expires_at.isoformat(),
        }


@dataclass
class PendingAuthorization:
    """State tracking for OAuth authorization flows."""

    state: str
    created_at: datetime
    client_id: str
    redirect_uri: AnyUrl
    redirect_uri_provided_explicitly: bool
    code_challenge: str
    scopes: list[str] | None
    resource: str | None
    client_state: str | None


@dataclass
class AuthorizationRecord:
    """Authorization code record mapped to a session."""

    authorization_code: AuthorizationCode
    session_id: str


@dataclass
class RefreshRecord:
    """Refresh token record mapped to a session."""

    refresh_token: OAuthRefreshToken
    session_id: str


class SessionStore:
    """In-memory store for Strava sessions and OAuth state."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._sessions_by_id: dict[str, StravaSession] = {}
        self._sessions_by_token: dict[str, StravaSession] = {}
        self._pending_states: dict[str, PendingAuthorization] = {}
        self._authorization_codes: dict[str, AuthorizationRecord] = {}
        self._access_tokens: dict[str, OAuthAccessToken] = {}
        self._refresh_tokens: dict[str, RefreshRecord] = {}
        self._clients: dict[str, OAuthClientInformationFull] = {}

    async def register_clients(
        self, clients: Mapping[str, Sequence[str]], scopes: Sequence[str]
    ) -> None:
        """Register OAuth clients allowed to use this MCP server."""
        scope_string = " ".join(scopes)
        async with self._lock:
            for client_id, redirect_uris in clients.items():
                try:
                    client = OAuthClientInformationFull.model_validate(
                        {
                            "client_id": client_id,
                            "redirect_uris": list(redirect_uris),
                            "token_endpoint_auth_method": "none",
                            "grant_types": ["authorization_code", "refresh_token"],
                            "response_types": ["code"],
                            "scope": scope_string or None,
                        }
                    )
                except ValidationError as exc:
                    raise ValueError(
                        f"Invalid redirect URIs for client '{client_id}': {exc}"
                    ) from exc
                self._clients[client_id] = client

    async def register_client_info(self, client_info: OAuthClientInformationFull) -> None:
        """Register or update an OAuth client entry."""
        async with self._lock:
            self._clients[client_info.client_id] = client_info

    async def get_client(self, client_id: str | None) -> OAuthClientInformationFull | None:
        """Lookup registered OAuth clients."""
        if not client_id:
            return None
        async with self._lock:
            return self._clients.get(client_id)

    async def create_authorization_request(
        self,
        *,
        client_id: str,
        redirect_uri: AnyUrl,
        redirect_uri_provided_explicitly: bool,
        code_challenge: str,
        scopes: list[str] | None,
        resource: str | None,
        client_state: str | None,
    ) -> PendingAuthorization:
        """Persist a pending authorization request."""
        state = secrets.token_urlsafe(16)
        pending = PendingAuthorization(
            state=state,
            created_at=self._now(),
            client_id=client_id,
            redirect_uri=redirect_uri,
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
            code_challenge=code_challenge,
            scopes=scopes,
            resource=resource,
            client_state=client_state,
        )
        async with self._lock:
            self._pending_states[state] = pending
        return pending

    async def pop_authorization_request(self, state: str) -> PendingAuthorization | None:
        """Remove and return a pending authorization request."""
        async with self._lock:
            return self._pending_states.pop(state, None)

    async def create_session(
        self, token_data: TokenResponse, scopes: Sequence[str]
    ) -> StravaSession:
        """Create and store a new Strava session based on exchange tokens."""
        now = self._now()
        session_id = secrets.token_urlsafe(16)

        expires_at = datetime.fromtimestamp(token_data.expires_at, tz=UTC)
        athlete = token_data.athlete.model_dump(mode="json") if token_data.athlete else None
        athlete_id = token_data.athlete.id if token_data.athlete else None
        athlete_name = (
            f"{token_data.athlete.firstname} {token_data.athlete.lastname}".strip()
            if token_data.athlete
            else None
        )

        session = StravaSession(
            session_id=session_id,
            access_token=token_data.access_token,
            refresh_token=token_data.refresh_token,
            expires_at=expires_at,
            scopes=list(scopes),
            created_at=now,
            updated_at=now,
            session_expires_at=now + SESSION_TTL,
            athlete=athlete,
            athlete_id=athlete_id,
            athlete_name=athlete_name or None,
        )

        async with self._lock:
            self._sessions_by_id[session_id] = session

        return session

    async def update_session_tokens(
        self, session: StravaSession, token_data: TokenResponse
    ) -> StravaSession:
        """Update Strava tokens for an existing session after a refresh."""
        now = self._now()
        async with self._lock:
            session.access_token = token_data.access_token
            session.refresh_token = token_data.refresh_token
            session.expires_at = datetime.fromtimestamp(token_data.expires_at, tz=UTC)
            session.updated_at = now
            session.session_expires_at = max(session.session_expires_at, now + SESSION_TTL)
            if token_data.athlete:
                session.athlete = token_data.athlete.model_dump(mode="json")
                session.athlete_id = token_data.athlete.id
                session.athlete_name = (
                    f"{token_data.athlete.firstname} {token_data.athlete.lastname}".strip()
                    or session.athlete_name
                )
        return session

    async def store_authorization_code(
        self,
        session: StravaSession,
        pending: PendingAuthorization,
    ) -> AuthorizationCode:
        """Create and persist an authorization code for the session."""
        scopes = pending.scopes or session.scopes
        code = secrets.token_urlsafe(32)
        authorization_code = AuthorizationCode(
            code=code,
            scopes=scopes,
            expires_at=time.time() + AUTHORIZATION_CODE_TTL_SECONDS,
            client_id=pending.client_id,
            code_challenge=pending.code_challenge,
            redirect_uri=pending.redirect_uri,
            redirect_uri_provided_explicitly=pending.redirect_uri_provided_explicitly,
            resource=pending.resource,
        )
        async with self._lock:
            self._authorization_codes[code] = AuthorizationRecord(
                authorization_code, session.session_id
            )
        return authorization_code

    async def load_authorization_code(self, code: str) -> AuthorizationCode | None:
        """Retrieve an authorization code without consuming it."""
        async with self._lock:
            record = self._authorization_codes.get(code)
            return record.authorization_code if record else None

    async def consume_authorization_code(
        self, code: str
    ) -> tuple[AuthorizationCode, StravaSession] | None:
        """Remove an authorization code and return the associated session."""
        async with self._lock:
            record = self._authorization_codes.pop(code, None)
            if record is None:
                return None
            session = self._sessions_by_id.get(record.session_id)
            if session is None or self._ensure_active_locked(session) is None:
                return None
            return record.authorization_code, session

    async def issue_tokens(
        self,
        session: StravaSession,
        *,
        client_id: str,
        scopes: Sequence[str],
        resource: str | None,
    ) -> OAuthToken:
        """Rotate and persist access/refresh tokens for the session."""
        async with self._lock:
            return self._issue_tokens_locked(
                session=session,
                client_id=client_id,
                scopes=list(scopes),
                resource=resource,
            )

    async def exchange_refresh_token(
        self,
        refresh_token: str,
        *,
        scopes: Sequence[str],
    ) -> tuple[OAuthToken, StravaSession] | None:
        """Rotate access/refresh tokens using a refresh token."""
        async with self._lock:
            record = self._refresh_tokens.pop(refresh_token, None)
            if record is None:
                return None

            session = self._sessions_by_id.get(record.session_id)
            if session is None or self._ensure_active_locked(session) is None:
                return None

            # Remove the old refresh token reference
            if session.oauth_refresh_token == refresh_token:
                session.oauth_refresh_token = None

            scopes_to_use = list(scopes) if scopes else record.refresh_token.scopes
            token = self._issue_tokens_locked(
                session=session,
                client_id=session.client_id or record.refresh_token.client_id,
                scopes=scopes_to_use,
                resource=session.resource,
            )
            return token, session

    async def get_session(self, session_id: str) -> StravaSession | None:
        """Retrieve a session by ID."""
        async with self._lock:
            session = self._sessions_by_id.get(session_id)
            return self._ensure_active_locked(session)

    async def get_session_by_token(self, token: str) -> StravaSession | None:
        """Retrieve a session from an MCP access token."""
        async with self._lock:
            session = self._sessions_by_token.get(token)
            return self._ensure_active_locked(session)

    async def get_access_token(self, token: str) -> OAuthAccessToken | None:
        """Return OAuth access token metadata."""
        async with self._lock:
            model = self._access_tokens.get(token)
            if not model:
                return None
            session = self._sessions_by_token.get(token)
            if self._ensure_active_locked(session) is None:
                self._access_tokens.pop(token, None)
                return None
            return model

    async def get_refresh_token(self, token: str) -> OAuthRefreshToken | None:
        """Return OAuth refresh token metadata."""
        async with self._lock:
            record = self._refresh_tokens.get(token)
            if not record:
                return None
            session = self._sessions_by_id.get(record.session_id)
            if self._ensure_active_locked(session) is None:
                self._refresh_tokens.pop(token, None)
                return None
            return record.refresh_token

    async def revoke_access_token(self, token: str) -> None:
        """Invalidate an access token."""
        async with self._lock:
            session = self._sessions_by_token.pop(token, None)
            self._access_tokens.pop(token, None)
            if session and session.mcp_token == token:
                session.mcp_token = None

    async def revoke_refresh_token(self, token: str) -> None:
        """Invalidate a refresh token."""
        async with self._lock:
            record = self._refresh_tokens.pop(token, None)
            if record:
                session = self._sessions_by_id.get(record.session_id)
                if session and session.oauth_refresh_token == token:
                    session.oauth_refresh_token = None

    async def remove_session(self, session_id: str) -> None:
        """Remove a session and related OAuth tokens from the store."""
        async with self._lock:
            session = self._sessions_by_id.pop(session_id, None)
            if not session:
                return

            self._remove_session_tokens_locked(session)

    def _issue_tokens_locked(
        self,
        *,
        session: StravaSession,
        client_id: str,
        scopes: list[str],
        resource: str | None,
    ) -> OAuthToken:
        """Internal helper to rotate access/refresh tokens (assumes lock held)."""
        now = self._now()
        scopes = scopes or session.scopes

        access_token = secrets.token_urlsafe(48)
        refresh_token = secrets.token_urlsafe(48)
        expires_at = int((now + SESSION_TTL).timestamp())

        # Clean up previous tokens
        self._remove_session_tokens_locked(session)

        access_model = OAuthAccessToken(
            token=access_token,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
            resource=resource,
        )
        refresh_model = OAuthRefreshToken(
            token=refresh_token,
            client_id=client_id,
            scopes=scopes,
        )

        self._access_tokens[access_token] = access_model
        self._refresh_tokens[refresh_token] = RefreshRecord(refresh_model, session.session_id)
        self._sessions_by_token[access_token] = session

        session.mcp_token = access_token
        session.oauth_refresh_token = refresh_token
        session.client_id = client_id
        session.resource = resource
        session.scopes = list(scopes)
        session.updated_at = now
        session.session_expires_at = now + SESSION_TTL

        return OAuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int((session.session_expires_at - now).total_seconds()),
            scope=" ".join(scopes) if scopes else None,
        )

    def _remove_session_tokens_locked(self, session: StravaSession) -> None:
        """Remove existing OAuth tokens associated with a session."""
        if session.mcp_token:
            self._access_tokens.pop(session.mcp_token, None)
            self._sessions_by_token.pop(session.mcp_token, None)
        if session.oauth_refresh_token:
            self._refresh_tokens.pop(session.oauth_refresh_token, None)
        session.mcp_token = None
        session.oauth_refresh_token = None

    def _ensure_active_locked(self, session: StravaSession | None) -> StravaSession | None:
        """Validate TTL and extend the session lifetime. Assumes lock held."""
        if session is None:
            return None

        now = self._now()
        if session.session_expires_at < now:
            # Session expired - remove it from the store.
            self._sessions_by_id.pop(session.session_id, None)
            if session.mcp_token:
                self._sessions_by_token.pop(session.mcp_token, None)
                self._access_tokens.pop(session.mcp_token, None)
            if session.oauth_refresh_token:
                self._refresh_tokens.pop(session.oauth_refresh_token, None)
            return None

        session.session_expires_at = now + SESSION_TTL
        return session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)


class DynamoSessionStore(SessionStore):
    """DynamoDB-backed implementation of the session store."""

    def __init__(
        self,
        table_name: str,
        *,
        region_name: str | None = None,
        boto3_resource: Any | None = None,
        ttl_seconds: int = DYNAMODB_DEFAULT_TTL_SECONDS,
    ) -> None:
        super().__init__()
        self._table_name = table_name
        self._ttl_seconds = ttl_seconds
        resource = boto3_resource or boto3.resource("dynamodb", region_name=region_name)  # type: ignore[reportUnknownMemberType]
        self._table = resource.Table(table_name)  # type: ignore[reportAttributeAccessIssue]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _session_key(session_id: str) -> str:
        return f"session:{session_id}"

    @staticmethod
    def _pending_key(state: str) -> str:
        return f"pending:{state}"

    @staticmethod
    def _authorization_code_key(code: str) -> str:
        return f"authorization_code:{code}"

    @staticmethod
    def _access_token_key(token: str) -> str:
        return f"access_token:{token}"

    @staticmethod
    def _refresh_token_key(token: str) -> str:
        return f"refresh_token:{token}"

    @staticmethod
    def _client_key(client_id: str) -> str:
        return f"client:{client_id}"

    def _ttl_timestamp(self, seconds: int | None = None) -> int:
        delta = seconds if seconds is not None else self._ttl_seconds
        return int(self._now().timestamp()) + delta

    async def _put_item(self, pk: str, data: dict[str, Any], *, ttl: int | None = None) -> None:
        item: dict[str, Any] = {"pk": pk, "data": json.dumps(data)}
        if ttl is not None:
            item["ttl"] = ttl
        await asyncio.to_thread(self._table.put_item, Item=item)  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]

    async def _get_item(self, pk: str) -> dict[str, Any] | None:
        response = await asyncio.to_thread(self._table.get_item, Key={"pk": pk})  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]
        item = response.get("Item")  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
        if item is None:
            return None
        data = json.loads(item["data"])  # type: ignore[reportUnknownArgumentType]
        return {"pk": item["pk"], "data": data, "ttl": item.get("ttl")}  # type: ignore[reportUnknownMemberType]

    async def _delete_item(self, pk: str) -> dict[str, Any] | None:
        response = await asyncio.to_thread(  # type: ignore[reportUnknownVariableType]
            self._table.delete_item,  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]
            Key={"pk": pk},
            ReturnValues="ALL_OLD",
        )
        attributes = response.get("Attributes")  # type: ignore[reportUnknownMemberType]
        if not attributes:
            return None
        data = json.loads(attributes["data"])  # type: ignore[reportUnknownArgumentType]
        return {"pk": attributes["pk"], "data": data, "ttl": attributes.get("ttl")}  # type: ignore[reportUnknownMemberType]

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_datetime(dt: datetime) -> str:
        return dt.astimezone(UTC).isoformat()

    @staticmethod
    def _deserialize_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _serialize_session(self, session: StravaSession) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": self._serialize_datetime(session.expires_at),
            "scopes": session.scopes,
            "created_at": self._serialize_datetime(session.created_at),
            "updated_at": self._serialize_datetime(session.updated_at),
            "session_expires_at": self._serialize_datetime(session.session_expires_at),
            "athlete": session.athlete,
            "athlete_id": session.athlete_id,
            "athlete_name": session.athlete_name,
            "mcp_token": session.mcp_token,
            "oauth_refresh_token": session.oauth_refresh_token,
            "client_id": session.client_id,
            "resource": session.resource,
        }

    def _deserialize_session(self, data: dict[str, Any]) -> StravaSession:
        session = StravaSession(
            session_id=data["session_id"],
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=self._deserialize_datetime(data["expires_at"]),
            scopes=list(data.get("scopes", [])),
            created_at=self._deserialize_datetime(data["created_at"]),
            updated_at=self._deserialize_datetime(data["updated_at"]),
            session_expires_at=self._deserialize_datetime(data["session_expires_at"]),
            athlete=data.get("athlete"),
            athlete_id=data.get("athlete_id"),
            athlete_name=data.get("athlete_name"),
        )
        session.mcp_token = data.get("mcp_token")
        session.oauth_refresh_token = data.get("oauth_refresh_token")
        session.client_id = data.get("client_id")
        session.resource = data.get("resource")
        return session

    @staticmethod
    def _serialize_pending(pending: PendingAuthorization) -> dict[str, Any]:
        return {
            "state": pending.state,
            "created_at": pending.created_at.isoformat(),
            "client_id": pending.client_id,
            "redirect_uri": str(pending.redirect_uri),
            "redirect_uri_provided_explicitly": pending.redirect_uri_provided_explicitly,
            "code_challenge": pending.code_challenge,
            "scopes": pending.scopes,
            "resource": pending.resource,
            "client_state": pending.client_state,
        }

    @staticmethod
    def _deserialize_pending(data: dict[str, Any]) -> PendingAuthorization:
        return PendingAuthorization(
            state=data["state"],
            created_at=datetime.fromisoformat(data["created_at"]),
            client_id=data["client_id"],
            redirect_uri=AnyUrl(data["redirect_uri"]),
            redirect_uri_provided_explicitly=data["redirect_uri_provided_explicitly"],
            code_challenge=data["code_challenge"],
            scopes=list(data["scopes"]) if data.get("scopes") else None,
            resource=data.get("resource"),
            client_state=data.get("client_state"),
        )

    @staticmethod
    def _serialize_authorization(record: AuthorizationRecord) -> dict[str, Any]:
        return {
            "session_id": record.session_id,
            "authorization_code": record.authorization_code.model_dump(mode="json"),
        }

    @staticmethod
    def _deserialize_authorization(data: dict[str, Any]) -> AuthorizationRecord:
        return AuthorizationRecord(
            AuthorizationCode.model_validate(data["authorization_code"]),
            data["session_id"],
        )

    @staticmethod
    def _serialize_access_token(token: OAuthAccessToken) -> dict[str, Any]:
        return token.model_dump(mode="json")

    @staticmethod
    def _serialize_refresh_record(record: RefreshRecord) -> dict[str, Any]:
        return {
            "session_id": record.session_id,
            "refresh_token": record.refresh_token.model_dump(mode="json"),
        }

    @staticmethod
    def _deserialize_access_token(data: dict[str, Any]) -> OAuthAccessToken:
        return OAuthAccessToken.model_validate(data)

    @staticmethod
    def _deserialize_refresh_record(data: dict[str, Any]) -> RefreshRecord:
        return RefreshRecord(
            OAuthRefreshToken.model_validate(data["refresh_token"]),
            data["session_id"],
        )

    @staticmethod
    def _deserialize_client(data: dict[str, Any]) -> OAuthClientInformationFull:
        return OAuthClientInformationFull.model_validate(data)

    async def _persist_session(self, session: StravaSession) -> None:
        await self._put_item(
            self._session_key(session.session_id),
            self._serialize_session(session),
            ttl=self._ttl_timestamp(),
        )

    async def _persist_access_token(self, session: StravaSession, token: OAuthAccessToken) -> None:
        await self._put_item(
            self._access_token_key(token.token),
            {
                "token": token.model_dump(mode="json"),
                "session_id": session.session_id,
            },
            ttl=self._ttl_timestamp(),
        )

    async def _persist_refresh_record(self, record: RefreshRecord) -> None:
        await self._put_item(
            self._refresh_token_key(record.refresh_token.token),
            self._serialize_refresh_record(record),
            ttl=self._ttl_timestamp(),
        )

    async def _delete_access_token(self, token: str) -> None:
        await self._delete_item(self._access_token_key(token))

    async def _delete_refresh_token(self, token: str) -> None:
        await self._delete_item(self._refresh_token_key(token))

    async def _delete_session(self, session_id: str) -> None:
        await self._delete_item(self._session_key(session_id))

    async def _delete_authorization_code(self, code: str) -> None:
        await self._delete_item(self._authorization_code_key(code))

    async def _delete_pending_state(self, state: str) -> None:
        await self._delete_item(self._pending_key(state))

    async def _hydrate_session(self, session_id: str) -> StravaSession | None:
        async with self._lock:
            session = self._sessions_by_id.get(session_id)
            if session is not None:
                return self._ensure_active_locked(session)
        item = await self._get_item(self._session_key(session_id))
        if not item:
            return None
        session = self._deserialize_session(item["data"])
        async with self._lock:
            self._sessions_by_id[session_id] = session
        return session

    async def _hydrate_refresh_record(self, token: str) -> RefreshRecord | None:
        async with self._lock:
            record = self._refresh_tokens.get(token)
            if record is not None:
                return record
        item = await self._get_item(self._refresh_token_key(token))
        if not item:
            return None
        record = self._deserialize_refresh_record(item["data"])
        await self._hydrate_session(record.session_id)
        async with self._lock:
            self._refresh_tokens[token] = record
        return record

    async def _hydrate_access_token(self, token: str) -> OAuthAccessToken | None:
        async with self._lock:
            access = self._access_tokens.get(token)
            if access is not None:
                return access
        item = await self._get_item(self._access_token_key(token))
        if not item:
            return None
        payload = item["data"]
        token_model = self._deserialize_access_token(payload["token"])
        session: StravaSession | None = None
        session_id = payload.get("session_id")
        if session_id:
            session = await self._hydrate_session(session_id)
        async with self._lock:
            self._access_tokens[token] = token_model
            if session is not None:
                self._sessions_by_token[token] = session
        return token_model

    async def _hydrate_authorization_record(self, code: str) -> AuthorizationRecord | None:
        async with self._lock:
            record = self._authorization_codes.get(code)
            if record is not None:
                return record
        item = await self._get_item(self._authorization_code_key(code))
        if not item:
            return None
        record = self._deserialize_authorization(item["data"])
        await self._hydrate_session(record.session_id)
        async with self._lock:
            self._authorization_codes[code] = record
        return record

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    async def register_clients(
        self, clients: Mapping[str, Sequence[str]], scopes: Sequence[str]
    ) -> None:
        await super().register_clients(clients, scopes)
        scope_string = " ".join(scopes)
        for client_id, redirect_uris in clients.items():
            payload = {
                "client_id": client_id,
                "redirect_uris": list(redirect_uris),
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "scope": scope_string or None,
            }
            await self._put_item(self._client_key(client_id), payload)

    async def register_client_info(self, client_info: OAuthClientInformationFull) -> None:
        await super().register_client_info(client_info)
        await self._put_item(
            self._client_key(client_info.client_id),
            client_info.model_dump(mode="json"),
        )

    async def get_client(self, client_id: str | None) -> OAuthClientInformationFull | None:
        client = await super().get_client(client_id)
        if client or not client_id:
            return client
        item = await self._get_item(self._client_key(client_id))
        if not item:
            return None
        client_info = self._deserialize_client(item["data"])
        async with self._lock:
            self._clients[client_info.client_id] = client_info
        return client_info

    async def create_authorization_request(
        self,
        *,
        client_id: str,
        redirect_uri: AnyUrl,
        redirect_uri_provided_explicitly: bool,
        code_challenge: str,
        scopes: list[str] | None,
        resource: str | None,
        client_state: str | None,
    ) -> PendingAuthorization:
        pending = await super().create_authorization_request(
            client_id=client_id,
            redirect_uri=redirect_uri,
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
            code_challenge=code_challenge,
            scopes=scopes,
            resource=resource,
            client_state=client_state,
        )
        await self._put_item(
            self._pending_key(pending.state),
            self._serialize_pending(pending),
            ttl=self._ttl_timestamp(AUTHORIZATION_CODE_TTL_SECONDS),
        )
        return pending

    async def pop_authorization_request(self, state: str) -> PendingAuthorization | None:
        pending = await super().pop_authorization_request(state)
        if pending:
            await self._delete_pending_state(state)
            return pending

        item = await self._delete_item(self._pending_key(state))
        if not item:
            return None
        return self._deserialize_pending(item["data"])

    async def create_session(
        self, token_data: TokenResponse, scopes: Sequence[str]
    ) -> StravaSession:
        session = await super().create_session(token_data, scopes)
        await self._persist_session(session)
        return session

    async def update_session_tokens(
        self, session: StravaSession, token_data: TokenResponse
    ) -> StravaSession:
        session = await super().update_session_tokens(session, token_data)
        await self._persist_session(session)
        return session

    async def store_authorization_code(
        self,
        session: StravaSession,
        pending: PendingAuthorization,
    ) -> AuthorizationCode:
        authorization_code = await super().store_authorization_code(session, pending)
        async with self._lock:
            record = self._authorization_codes.get(authorization_code.code)
        if record:
            await self._put_item(
                self._authorization_code_key(authorization_code.code),
                self._serialize_authorization(record),
                ttl=self._ttl_timestamp(AUTHORIZATION_CODE_TTL_SECONDS),
            )
        return authorization_code

    async def load_authorization_code(self, code: str) -> AuthorizationCode | None:
        authorization = await super().load_authorization_code(code)
        if authorization:
            return authorization
        record = await self._hydrate_authorization_record(code)
        return record.authorization_code if record else None

    async def consume_authorization_code(
        self, code: str
    ) -> tuple[AuthorizationCode, StravaSession] | None:
        result = await super().consume_authorization_code(code)
        if result:
            authorization_code, session = result
            await self._delete_authorization_code(code)
            return authorization_code, session

        item = await self._delete_item(self._authorization_code_key(code))
        if not item:
            return None
        record = self._deserialize_authorization(item["data"])
        session = await self._hydrate_session(record.session_id)
        if session is None:
            return None
        return record.authorization_code, session

    async def issue_tokens(
        self,
        session: StravaSession,
        *,
        client_id: str,
        scopes: Sequence[str],
        resource: str | None,
    ) -> OAuthToken:
        async with self._lock:
            old_access = session.mcp_token
            old_refresh = session.oauth_refresh_token
            token = self._issue_tokens_locked(
                session=session,
                client_id=client_id,
                scopes=list(scopes),
                resource=resource,
            )
            access_model = self._access_tokens[token.access_token]
            assert token.refresh_token is not None, "Refresh token must be present"
            refresh_record = self._refresh_tokens[token.refresh_token]
            session_snapshot = self._sessions_by_id[session.session_id]

        if old_access:
            await self._delete_access_token(old_access)
        if old_refresh:
            await self._delete_refresh_token(old_refresh)

        await self._persist_session(session_snapshot)
        await self._persist_access_token(session_snapshot, access_model)
        await self._persist_refresh_record(refresh_record)
        return token

    async def exchange_refresh_token(
        self,
        refresh_token: str,
        *,
        scopes: Sequence[str],
    ) -> tuple[OAuthToken, StravaSession] | None:
        record = await self._hydrate_refresh_record(refresh_token)
        if record is None:
            return None

        async with self._lock:
            stored = self._refresh_tokens.pop(refresh_token, None)
            if stored is None:
                # Another invocation removed it between hydrate and now
                record = None
            else:
                record = stored

        if record is None:
            return None

        async with self._lock:
            session = self._sessions_by_id.get(record.session_id)
            if session is None or self._ensure_active_locked(session) is None:
                return None
            old_access = session.mcp_token
            old_refresh = session.oauth_refresh_token
            scopes_to_use = list(scopes) if scopes else record.refresh_token.scopes
            token = self._issue_tokens_locked(
                session=session,
                client_id=session.client_id or record.refresh_token.client_id,
                scopes=scopes_to_use,
                resource=session.resource,
            )
            access_model = self._access_tokens[token.access_token]
            assert token.refresh_token is not None, "Refresh token must be present"
            refresh_record = self._refresh_tokens[token.refresh_token]
            session_snapshot = self._sessions_by_id[session.session_id]

        if old_access:
            await self._delete_access_token(old_access)
        if old_refresh:
            await self._delete_refresh_token(old_refresh)
        await self._delete_refresh_token(refresh_token)

        await self._persist_session(session_snapshot)
        await self._persist_access_token(session_snapshot, access_model)
        await self._persist_refresh_record(refresh_record)
        return token, session_snapshot

    async def get_session(self, session_id: str) -> StravaSession | None:
        session = await super().get_session(session_id)
        if session:
            return session
        return await self._hydrate_session(session_id)

    async def get_session_by_token(self, token: str) -> StravaSession | None:
        session = await super().get_session_by_token(token)
        if session:
            return session
        item = await self._get_item(self._access_token_key(token))
        if not item:
            return None
        session_id = item["data"].get("session_id")
        if not session_id:
            return None
        session = await self._hydrate_session(session_id)
        if session is None:
            return None
        async with self._lock:
            self._sessions_by_token[token] = session
        return session

    async def get_access_token(self, token: str) -> OAuthAccessToken | None:
        access = await super().get_access_token(token)
        if access:
            return access
        return await self._hydrate_access_token(token)

    async def get_refresh_token(self, token: str) -> OAuthRefreshToken | None:
        refresh = await super().get_refresh_token(token)
        if refresh:
            return refresh
        record = await self._hydrate_refresh_record(token)
        return record.refresh_token if record else None

    async def revoke_access_token(self, token: str) -> None:
        await super().revoke_access_token(token)
        await self._delete_access_token(token)

    async def revoke_refresh_token(self, token: str) -> None:
        await super().revoke_refresh_token(token)
        await self._delete_refresh_token(token)

    async def remove_session(self, session_id: str) -> None:
        session = await self.get_session(session_id)
        await super().remove_session(session_id)
        await self._delete_session(session_id)
        if session:
            if session.mcp_token:
                await self._delete_access_token(session.mcp_token)
            if session.oauth_refresh_token:
                await self._delete_refresh_token(session.oauth_refresh_token)


class StravaOAuthService:
    """Handle Strava OAuth flows and token refreshes."""

    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/oauth/token"

    def __init__(
        self,
        app_config: StravaAppConfig,
        session_store: SessionStore,
        base_url: str,
        scopes: list[str] | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("A base URL is required for OAuth callbacks.")

        if isinstance(base_url, AnyHttpUrl):
            base_url = str(base_url)

        self.app_config = app_config
        self.session_store = session_store
        self.base_url = base_url.rstrip("/")
        self.redirect_uri = f"{self.base_url}/oauth/strava/callback"
        self.scopes = scopes or _parse_scopes(app_config)

    def build_authorization_url(self, state: str) -> str:
        """Generate the Strava authorization URL for the given state."""
        params = {
            "client_id": self.app_config.strava_client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": ",".join(self.scopes),
            "approval_prompt": "auto",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> TokenResponse:
        """Exchange an authorization code for OAuth tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.app_config.strava_client_id,
                    "client_secret": self.app_config.strava_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return TokenResponse(**response.json())

    async def refresh_session(self, session: StravaSession) -> StravaSession:
        """Refresh a Strava session's access token using its refresh token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.app_config.strava_client_id,
                    "client_secret": self.app_config.strava_client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": session.refresh_token,
                },
            )
            response.raise_for_status()
            token_data = TokenResponse(**response.json())
        return await self.session_store.update_session_tokens(session, token_data)

    async def create_session_from_code(self, code: str) -> StravaSession:
        """Complete the OAuth authorization code flow and persist a session."""
        token_data = await self.exchange_code(code)
        return await self.session_store.create_session(token_data, self.scopes)


def create_session_store_from_env() -> SessionStore:
    """Instantiate the appropriate session store based on environment configuration."""
    backend = os.getenv("STRAVA_SESSION_BACKEND", "").strip().lower()
    if backend == "dynamodb":
        table_name = os.getenv("STRAVA_SESSION_TABLE")
        if not table_name:
            raise ValueError(
                "STRAVA_SESSION_TABLE must be set when STRAVA_SESSION_BACKEND=dynamodb."
            )
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        ttl_env = os.getenv("STRAVA_SESSION_TTL_SECONDS")
        ttl_seconds = (
            int(ttl_env) if ttl_env and ttl_env.isdigit() else DYNAMODB_DEFAULT_TTL_SECONDS
        )
        return DynamoSessionStore(
            table_name=table_name,
            region_name=region,
            ttl_seconds=ttl_seconds,
        )
    return SessionStore()


class HttpStravaAuthContext:
    """HTTP mode: Per-request context combining app configuration and user session.

    Multi-user authentication where each request resolves to a specific user's session.
    Token refresh updates the session in SessionStore (in-memory or DynamoDB).
    """

    def __init__(
        self,
        app_config: StravaAppConfig,
        session: StravaSession,
        session_store: SessionStore,
        oauth_service: StravaOAuthService,
    ) -> None:
        self.app_config = app_config
        self.session = session
        self._session_store = session_store
        self._oauth_service = oauth_service
        self._refresh_lock = asyncio.Lock()

    @property
    def strava_client_id(self) -> str:
        return self.app_config.strava_client_id

    @property
    def strava_client_secret(self) -> str:
        return self.app_config.strava_client_secret

    @property
    def strava_measurement_preference(self) -> Literal["meters", "feet"]:
        return self.app_config.strava_measurement_preference

    @property
    def route_export_path(self) -> str:
        return self.app_config.route_export_path

    @property
    def strava_access_token(self) -> str:
        return self.session.access_token

    @property
    def strava_refresh_token(self) -> str:
        return self.session.refresh_token

    @property
    def session_id(self) -> str:
        return self.session.session_id

    @property
    def athlete_id(self) -> int | None:
        return self.session.athlete_id

    @property
    def athlete_name(self) -> str | None:
        return self.session.athlete_name

    @property
    def expires_at(self) -> datetime:
        return self.session.expires_at

    async def ensure_active(self) -> None:
        """Refresh the Strava token if it is close to expiry."""
        if self.session.expires_at - TOKEN_REFRESH_SKEW > datetime.now(UTC):
            return
        await self.refresh_tokens()

    async def refresh_tokens(self) -> None:
        """Force a refresh of the Strava access token."""
        async with self._refresh_lock:
            if self.session.expires_at - TOKEN_REFRESH_SKEW > datetime.now(UTC):
                return
            await self._oauth_service.refresh_session(self.session)

    async def detach(self) -> None:
        """Remove the session from the store (e.g., logout)."""
        await self._session_store.remove_session(self.session.session_id)
