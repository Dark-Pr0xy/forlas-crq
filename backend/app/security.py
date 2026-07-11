"""Password hashing and session-cookie signing."""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from app.config import settings

_hasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost_kib,
    parallelism=settings.argon2_parallelism,
)
_signer = TimestampSigner(settings.secret_key, salt="forlas.session")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)


def sign_session(user_id: int) -> str:
    # Append a random nonce so two sessions issued for the same user within the
    # same second (e.g. setup-then-login, or rapid re-auth) never collide on the
    # unique token constraint. TimestampSigner keeps the "<id>.<nonce>" payload
    # intact; the nonce is url-safe base64 and never contains a ".".
    nonce = secrets.token_urlsafe(9)
    payload = f"{user_id}.{nonce}"
    return _signer.sign(payload.encode("utf-8")).decode("utf-8")


def verify_session(token: str) -> int | None:
    max_age = settings.session_ttl_hours * 3600
    try:
        raw = _signer.unsign(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # Payload is "<user_id>.<nonce>" (or a bare "<user_id>" from older tokens).
    try:
        return int(text.split(".", 1)[0])
    except ValueError:
        return None
