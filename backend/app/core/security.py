from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

_hasher = PasswordHasher()
_serializer = URLSafeTimedSerializer(settings.session_secret)

PARENT_COOKIE = "parent_session"
CHILD_COOKIE = "child_session"
PARENT_MAX_AGE = 60 * 60 * 24 * 7
CHILD_MAX_AGE = 60 * 60 * 2


def hash_secret(secret: str) -> str:
    """Hash a password or PIN with Argon2."""
    return _hasher.hash(secret)


def verify_secret(secret: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, secret)
    except VerifyMismatchError:
        return False


def sign_session(payload: dict[str, str], salt: str) -> str:
    return _serializer.dumps(payload, salt=salt)


def read_session(token: str, salt: str, max_age: int) -> dict[str, str] | None:
    try:
        data = _serializer.loads(token, salt=salt, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    return data if isinstance(data, dict) else None
