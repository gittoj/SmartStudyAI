"""Database-backed rate limits, so they survive restarts and work across several API processes.

Events are stored under a keyed hash of the email or IP address (never the raw value) and purged
after a day. Only failures are counted for login, so normal use is never limited."""
import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import RateLimitEvent

logger = logging.getLogger(__name__)
TOO_MANY_MESSAGE = "Too many tries. Please wait a few minutes and try again."


def _digest(scope: str, key: str) -> str:
    return hmac.new(settings.session_secret.encode(), f"{scope}:{key}".encode(), hashlib.sha256).hexdigest()


def client_ip(request: Request) -> str:
    """The caller's address. A proxy header is used only when TRUST_PROXY_HEADER names one."""
    header = settings.trust_proxy_header.strip().lower()
    if header:
        first = request.headers.get(header, "").split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


async def ensure_allowed(db, scope: str, key: str, limit: int, window: timedelta) -> None:
    """Raise 429 when this key already has `limit` events inside the window."""
    since = datetime.now(timezone.utc) - window
    count = (await db.execute(
        select(func.count()).select_from(RateLimitEvent).where(
            RateLimitEvent.scope == scope, RateLimitEvent.key == _digest(scope, key),
            RateLimitEvent.created_at > since)
    )).scalar_one()
    if count >= limit:
        logger.warning("rate_limit scope=%s blocked", scope)
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, TOO_MANY_MESSAGE,
                            headers={"Retry-After": str(int(window.total_seconds()))})


async def record(db, scope: str, key: str) -> None:
    db.add(RateLimitEvent(scope=scope, key=_digest(scope, key)))
    await db.commit()


async def clear(db, scope: str, key: str) -> None:
    """A successful login wipes that account's failure count."""
    await db.execute(delete(RateLimitEvent).where(
        RateLimitEvent.scope == scope, RateLimitEvent.key == _digest(scope, key)))
    await db.commit()


async def purge_old_events(session_factory=SessionLocal, older_than: timedelta = timedelta(days=1)) -> int:
    cutoff = datetime.now(timezone.utc) - older_than
    async with session_factory() as db:
        result = await db.execute(delete(RateLimitEvent).where(RateLimitEvent.created_at < cutoff))
        await db.commit()
    return result.rowcount or 0
