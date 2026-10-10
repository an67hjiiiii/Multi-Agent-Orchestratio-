from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Mapping


AUTH_SCHEMA_VERSION = "local-auth-v1"
DEFAULT_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
PASSWORD_ITERATIONS = 240_000
PASSWORD_MIN_LENGTH = 8
USER_ROLES = frozenset({"USER", "ADMIN"})
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,63}$")


class DuplicateUserError(ValueError):
    """Raised when an email or username is already registered."""


class InvalidCredentialsError(ValueError):
    """Raised when a login identifier/password pair is not valid."""


class InvalidSessionError(ValueError):
    """Raised when a session token is missing, expired, or revoked."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalized_email(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _normalized_username(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        salt.hex(),
        digest.hex(),
    )


def _password_matches(password: str, encoded: object) -> bool:
    if not isinstance(encoded, str):
        return False
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iteration_count = int(iterations)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (TypeError, ValueError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iteration_count,
    )
    return hmac.compare_digest(actual, expected)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthStore:
    """A small file-backed local auth/session boundary.

    The store persists only password hashes and session-token hashes.  Raw
    passwords and tokens are returned to the caller only at registration or
    login time, which keeps the on-disk record useful for local restart while
    avoiding credential exposure in API responses or JSON files.
    """

    def __init__(
        self,
        root: str | Path = "data",
        *,
        session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "auth.json"
        self.session_ttl_seconds = max(60, int(session_ttl_seconds))
        self._lock = RLock()
        self._data: dict[str, Any] = {
            "schema_version": AUTH_SCHEMA_VERSION,
            "users": [],
            "sessions": [],
        }
        self._load()
        self._bootstrap_admin_from_environment()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("auth store is not valid UTF-8 JSON") from exc
        if not isinstance(raw, Mapping):
            raise ValueError("auth store root must be a JSON object")
        users = raw.get("users", [])
        sessions = raw.get("sessions", [])
        if not isinstance(users, list) or not isinstance(sessions, list):
            raise ValueError("auth store users and sessions must be JSON arrays")
        self._data = {
            "schema_version": str(raw.get("schema_version") or AUTH_SCHEMA_VERSION),
            "users": [dict(item) for item in users if isinstance(item, Mapping)],
            "sessions": [dict(item) for item in sessions if isinstance(item, Mapping)],
        }

    def _save(self) -> None:
        payload = json.dumps(self._data, ensure_ascii=False, indent=2)
        temporary_path: str | None = None
        try:
            fd, temporary_path = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.root,
                text=True,
            )
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    @staticmethod
    def _public_user(user: Mapping[str, Any]) -> dict[str, Any]:
        user_id = str(user.get("user_id") or user.get("id") or "")
        display_name = str(
            user.get("display_name") or user.get("name") or user.get("username") or ""
        )
        return {
            "id": user_id,
            "user_id": user_id,
            "email": user.get("email"),
            "username": user.get("username"),
            "name": display_name,
            "display_name": display_name,
            "role": str(user.get("role") or "USER").upper(),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at"),
            "last_login_at": user.get("last_login_at"),
            "status": str(user.get("status") or "ACTIVE").upper(),
        }

    @staticmethod
    def _public_session(session: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "session_id": session.get("session_id"),
            "user_id": session.get("user_id"),
            "created_at": session.get("created_at"),
            "expires_at": session.get("expires_at"),
        }

    def _users(self) -> list[dict[str, Any]]:
        users = self._data.get("users")
        if not isinstance(users, list):
            self._data["users"] = []
            return self._data["users"]
        return users

    def _sessions(self) -> list[dict[str, Any]]:
        sessions = self._data.get("sessions")
        if not isinstance(sessions, list):
            self._data["sessions"] = []
            return self._data["sessions"]
        return sessions

    def _purge_sessions(self, *, now: datetime | None = None) -> bool:
        now = now or _utc_now()
        sessions = self._sessions()
        kept: list[dict[str, Any]] = []
        changed = False
        for session in sessions:
            expires_at = _parse_iso(session.get("expires_at"))
            revoked_at = session.get("revoked_at")
            if expires_at is None or expires_at <= now or revoked_at:
                changed = True
                continue
            kept.append(session)
        if changed:
            self._data["sessions"] = kept
        return changed

    def _bootstrap_admin_from_environment(self) -> None:
        """Optionally create an admin only when the local store is empty.

        This is deliberately opt-in and environment-driven so a normal local
        registration cannot silently turn itself into an administrator after
        the first account exists.  The password is hashed immediately and is
        never written to the store or returned by the API.
        """

        email = _normalized_email(os.getenv("LOCAL_AUTH_ADMIN_EMAIL"))
        password = os.getenv("LOCAL_AUTH_ADMIN_PASSWORD", "")
        if not email or len(password) < PASSWORD_MIN_LENGTH:
            return
        with self._lock:
            if self._users():
                return
            now = _iso(_utc_now())
            self._users().append(
                {
                    "user_id": f"usr_{secrets.token_urlsafe(12)}",
                    "email": email,
                    "username": None,
                    "display_name": email.split("@", 1)[0],
                    "role": "ADMIN",
                    "status": "ACTIVE",
                    "password_hash": _password_hash(password),
                    "created_at": now,
                    "updated_at": now,
                    "last_login_at": None,
                }
            )
            self._save()

    def register(
        self,
        *,
        password: str,
        email: str | None = None,
        username: str | None = None,
        display_name: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        email_value = _normalized_email(email)
        username_value = _normalized_username(username)
        if not email_value and not username_value:
            raise ValueError("email or username is required")
        if email_value and ("@" not in email_value or len(email_value) > 254):
            raise ValueError("email is invalid")
        if username_value and not _USERNAME_PATTERN.fullmatch(username_value):
            raise ValueError("username is invalid")
        if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"password must be at least {PASSWORD_MIN_LENGTH} characters"
            )
        requested_role = str(role or "USER").strip().upper()
        if requested_role not in USER_ROLES:
            raise ValueError("role must be USER or ADMIN")

        with self._lock:
            now = _iso(_utc_now())
            users = self._users()
            for existing in users:
                if email_value and _normalized_email(existing.get("email")) == email_value:
                    raise DuplicateUserError("email is already registered")
                if username_value and _normalized_username(existing.get("username")) == username_value:
                    raise DuplicateUserError("username is already registered")

            # ADMIN is a bootstrap role only: it can be requested for the
            # first local account (or supplied by the opt-in env bootstrap),
            # but later self-registration is always USER.
            assigned_role = requested_role if not users else "USER"
            name = (display_name or username_value or email_value.split("@", 1)[0]).strip()
            user = {
                "user_id": f"usr_{secrets.token_urlsafe(12)}",
                "email": email_value or None,
                "username": username_value or None,
                "display_name": name,
                "role": assigned_role,
                "status": "ACTIVE",
                "password_hash": _password_hash(password),
                "created_at": now,
                "updated_at": now,
                "last_login_at": None,
            }
            users.append(user)
            self._save()
            return self._public_user(user)

    def authenticate(self, *, identifier: str, password: str) -> tuple[dict[str, Any], str, dict[str, Any]]:
        normalized_identifier = str(identifier or "").strip().lower()
        if not normalized_identifier or not isinstance(password, str):
            raise InvalidCredentialsError("invalid credentials")
        with self._lock:
            user = next(
                (
                    item
                    for item in self._users()
                    if normalized_identifier
                    in {
                        _normalized_email(item.get("email")),
                        _normalized_username(item.get("username")),
                    }
                ),
                None,
            )
            if user is None or str(user.get("status") or "ACTIVE").upper() != "ACTIVE":
                raise InvalidCredentialsError("invalid credentials")
            if not _password_matches(password, user.get("password_hash")):
                raise InvalidCredentialsError("invalid credentials")

            now = _utc_now()
            now_text = _iso(now)
            user["last_login_at"] = now_text
            user["updated_at"] = now_text
            token = secrets.token_urlsafe(32)
            session = {
                "session_id": f"ses_{secrets.token_urlsafe(12)}",
                "user_id": user.get("user_id"),
                "token_hash": _token_hash(token),
                "created_at": now_text,
                "expires_at": _iso(now + timedelta(seconds=self.session_ttl_seconds)),
            }
            self._purge_sessions(now=now)
            self._sessions().append(session)
            self._save()
            return self._public_user(user), token, self._public_session(session)

    def create_session(self, user_id: str) -> tuple[str, dict[str, Any]]:
        """Create a session for an existing user without exposing credentials."""

        with self._lock:
            user = next((item for item in self._users() if item.get("user_id") == user_id), None)
            if user is None:
                raise InvalidCredentialsError("user not found")
            now = _utc_now()
            token = secrets.token_urlsafe(32)
            session = {
                "session_id": f"ses_{secrets.token_urlsafe(12)}",
                "user_id": user_id,
                "token_hash": _token_hash(token),
                "created_at": _iso(now),
                "expires_at": _iso(now + timedelta(seconds=self.session_ttl_seconds)),
            }
            self._purge_sessions(now=now)
            self._sessions().append(session)
            self._save()
            return token, self._public_session(session)

    def resolve(self, token: str | None) -> dict[str, Any]:
        if not isinstance(token, str) or not token.strip():
            raise InvalidSessionError("authentication is required")
        digest = _token_hash(token.strip())
        with self._lock:
            now = _utc_now()
            changed = self._purge_sessions(now=now)
            session = next(
                (item for item in self._sessions() if hmac.compare_digest(str(item.get("token_hash") or ""), digest)),
                None,
            )
            if session is None:
                if changed:
                    self._save()
                raise InvalidSessionError("session is invalid or expired")
            user = next((item for item in self._users() if item.get("user_id") == session.get("user_id")), None)
            if user is None or str(user.get("status") or "ACTIVE").upper() != "ACTIVE":
                if changed:
                    self._save()
                raise InvalidSessionError("session is invalid or expired")
            if changed:
                self._save()
            return self._public_user(user)

    def revoke(self, token: str | None) -> bool:
        if not isinstance(token, str) or not token.strip():
            return False
        digest = _token_hash(token.strip())
        with self._lock:
            before = len(self._sessions())
            self._data["sessions"] = [
                item
                for item in self._sessions()
                if not hmac.compare_digest(str(item.get("token_hash") or ""), digest)
            ]
            changed = len(self._sessions()) != before
            if self._purge_sessions():
                changed = True
            if changed:
                self._save()
            return changed

    def list_users(self, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        with self._lock:
            rows = sorted(
                self._users(),
                key=lambda item: (str(item.get("created_at") or ""), str(item.get("user_id") or "")),
                reverse=True,
            )
            return [self._public_user(item) for item in rows[offset : offset + limit]]

    def user_count(self) -> int:
        with self._lock:
            return len(self._users())

    def status(self) -> dict[str, Any]:
        with self._lock:
            changed = self._purge_sessions()
            if changed:
                self._save()
            active_sessions = len(self._sessions())
            admin_count = sum(
                1 for item in self._users() if str(item.get("role") or "").upper() == "ADMIN"
            )
            return {
                "schema_version": AUTH_SCHEMA_VERSION,
                "local_only": True,
                "user_count": len(self._users()),
                "admin_count": admin_count,
                "active_session_count": active_sessions,
                "session_ttl_seconds": self.session_ttl_seconds,
            }

    def session_for_token(self, token: str | None) -> dict[str, Any] | None:
        if not isinstance(token, str) or not token.strip():
            return None
        digest = _token_hash(token.strip())
        with self._lock:
            now = _utc_now()
            changed = self._purge_sessions(now=now)
            session = next(
                (item for item in self._sessions() if hmac.compare_digest(str(item.get("token_hash") or ""), digest)),
                None,
            )
            if changed:
                self._save()
            return None if session is None else self._public_session(session)
