"""Private worksheet file storage in Postgres (table `stored_files`). The worksheet row stores only the key.

Files live in the database so the backend can run on hosts without a persistent disk. Each call uses
its own short session, so a stored file does not depend on the caller's transaction (the same
behaviour the earlier disk storage had). Swap these three functions for S3/GCS later; callers only
see keys."""
import re
import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import SessionLocal
from app.models import StoredFile

# Replaced in tests with a session factory bound to a throwaway database.
session_factory: async_sessionmaker[AsyncSession] = SessionLocal

_KEY_PATTERN = re.compile(r"^[0-9a-f-]{36}/[0-9a-f]{32}(\.[a-z0-9]{1,8})?$")


def _check_key(key: str) -> str:
    """Only server-generated keys are accepted, so a stray value can never address another record."""
    if not _KEY_PATTERN.fullmatch(key):
        raise ValueError("Invalid storage key")
    return key


def new_storage_key(child_id: uuid.UUID, extension: str) -> str:
    """Server-generated key; the client's file name never becomes part of the key."""
    return _check_key(f"{child_id}/{uuid.uuid4().hex}{extension}")


async def save_file(key: str, data: bytes) -> None:
    async with session_factory() as db:
        db.add(StoredFile(key=_check_key(key), data=data))
        await db.commit()


async def read_file(key: str) -> bytes:
    """Raise FileNotFoundError when the file is gone (for example, already purged)."""
    async with session_factory() as db:
        stored = await db.get(StoredFile, _check_key(key))
    if stored is None:
        raise FileNotFoundError(key)
    return stored.data


async def delete_file(key: str) -> None:
    """Missing files are ignored, like unlink(missing_ok=True)."""
    async with session_factory() as db:
        await db.execute(delete(StoredFile).where(StoredFile.key == _check_key(key)))
        await db.commit()
