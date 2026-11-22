"""Private worksheet file storage on local disk. The database stores only the key.
Swap the three functions for S3/GCS later; callers only see keys."""
import asyncio
import uuid
from pathlib import Path

from app.core.config import settings


def _resolve(key: str) -> Path:
    root = Path(settings.storage_dir).resolve()
    path = (root / key).resolve()
    if root not in path.parents:
        raise ValueError("Invalid storage key")
    return path


def new_storage_key(child_id: uuid.UUID, extension: str) -> str:
    """Server-generated key; the client's file name never becomes part of the path."""
    return f"{child_id}/{uuid.uuid4().hex}{extension}"


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


async def save_file(key: str, data: bytes) -> None:
    await asyncio.to_thread(_write, _resolve(key), data)


async def read_file(key: str) -> bytes:
    return await asyncio.to_thread(_resolve(key).read_bytes)


async def delete_file(key: str) -> None:
    await asyncio.to_thread(_resolve(key).unlink, True)  # missing_ok
