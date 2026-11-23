"""Deployment plumbing: database-backed file storage, host URL normalisation and the proxy secret."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import normalize_database_url, settings
from app.main import app
from app.models import Base
from app.services import storage_service


@pytest.fixture
async def storage(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(storage_service, "session_factory", async_sessionmaker(engine, expire_on_commit=False))
    yield
    await engine.dispose()


async def test_file_round_trip_and_delete(storage):
    key = storage_service.new_storage_key(uuid.uuid4(), ".pdf")
    await storage_service.save_file(key, b"%PDF-1.7 worksheet")
    assert await storage_service.read_file(key) == b"%PDF-1.7 worksheet"
    await storage_service.delete_file(key)
    with pytest.raises(FileNotFoundError):
        await storage_service.read_file(key)
    await storage_service.delete_file(key)  # deleting twice is fine


@pytest.mark.parametrize("key", ["../etc/passwd", "k.png", "child/file.pdf", ""])
async def test_rejects_keys_the_server_did_not_generate(storage, key):
    with pytest.raises(ValueError):
        await storage_service.read_file(key)


@pytest.mark.parametrize(("given", "expected"), [
    ("postgresql://u:p@ep-x.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
     "postgresql+asyncpg://u:p@ep-x.ap-southeast-1.aws.neon.tech/neondb?ssl=require"),
    ("postgres://u:p@host:5432/db", "postgresql+asyncpg://u:p@host:5432/db"),
    ("postgresql+asyncpg://u:p@localhost:5432/smartstudy", "postgresql+asyncpg://u:p@localhost:5432/smartstudy"),
    ("sqlite+aiosqlite:///:memory:", "sqlite+aiosqlite:///:memory:"),
])
def test_normalize_database_url(given, expected):
    assert normalize_database_url(given) == expected


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_proxy_secret_blocks_direct_calls(monkeypatch, client):
    monkeypatch.setattr(settings, "proxy_shared_secret", "s3cret-value")
    async with client:
        assert (await client.get("/api/auth/me")).status_code == 404
        assert (await client.get("/api/auth/me", headers={"x-proxy-secret": "wrong"})).status_code == 404
        # Right secret gets through to the route itself (401 because nobody is logged in).
        assert (await client.get("/api/auth/me", headers={"x-proxy-secret": "s3cret-value"})).status_code == 401
        assert (await client.get("/health")).status_code == 200  # host health checks need no secret


async def test_no_secret_configured_means_no_check(monkeypatch, client):
    monkeypatch.setattr(settings, "proxy_shared_secret", "")
    async with client:
        assert (await client.get("/api/auth/me")).status_code == 401
