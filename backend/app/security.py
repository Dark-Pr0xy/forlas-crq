"""Password hashing and session-cookie signing."""

from __future__ import annotations

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
    return _signer.sign(str(user_id).encode("utf-8")).decode("utf-8")


def verify_session(token: str) -> int | None:
    max_age = settings.session_ttl_hours * 3600
    try:
        raw = _signer.unsign(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    try:
        return int(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
