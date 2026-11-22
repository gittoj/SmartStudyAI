from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.models import RateLimitEvent
from app.services import rate_limit_service
from tests.test_practice_dashboard import PASSWORD, env, register_and_login  # noqa: F401  (env is a fixture)


async def attempt(client, email: str, password: str):
    return await client.post("/api/auth/login", json={"email": email, "password": password})


async def test_repeated_wrong_passwords_block_that_email_even_for_the_right_one(env, monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_fail_limit_email", 3)
    _, make_client = env
    async with make_client() as client:
        await register_and_login(client)
        for _ in range(3):
            assert (await attempt(client, "p@example.com", "wrong-password-1")).status_code == 401
        blocked = await attempt(client, "p@example.com", PASSWORD)
        assert blocked.status_code == 429 and blocked.headers["retry-after"] == "900"
        # another account is not affected by this email's failures
        assert (await attempt(client, "other@example.com", "wrong-password-1")).status_code == 401


async def test_a_successful_login_clears_the_failure_count(env, monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_fail_limit_email", 3)
    _, make_client = env
    async with make_client() as client:
        await register_and_login(client)
        for _ in range(2):
            await attempt(client, "p@example.com", "wrong-password-1")
        assert (await attempt(client, "p@example.com", PASSWORD)).status_code == 200
        for _ in range(2):
            assert (await attempt(client, "p@example.com", "wrong-password-1")).status_code == 401  # not 429


async def test_one_address_trying_many_emails_is_blocked(env, monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_fail_limit_ip", 2)
    _, make_client = env
    async with make_client() as client:
        for number in range(2):
            assert (await attempt(client, f"nobody{number}@example.com", "wrong-password-1")).status_code == 401
        assert (await attempt(client, "nobody9@example.com", "wrong-password-1")).status_code == 429


async def test_unknown_emails_are_limited_the_same_way_as_real_ones(env, monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_fail_limit_email", 2)
    _, make_client = env
    async with make_client() as client:
        for _ in range(2):
            assert (await attempt(client, "ghost@example.com", "wrong-password-1")).status_code == 401
        assert (await attempt(client, "ghost@example.com", "wrong-password-1")).status_code == 429


async def test_too_many_sign_ups_from_one_address_are_blocked(env, monkeypatch) -> None:
    monkeypatch.setattr(settings, "register_limit_ip", 2)
    _, make_client = env
    async with make_client() as client:
        for number in range(2):
            body = {"email": f"p{number}@example.com", "displayName": "P", "password": PASSWORD}
            assert (await client.post("/api/auth/register", json=body)).status_code == 201
        body = {"email": "p9@example.com", "displayName": "P", "password": PASSWORD}
        assert (await client.post("/api/auth/register", json=body)).status_code == 429


async def test_events_hold_no_raw_email_or_address_and_old_ones_are_purged(env, monkeypatch) -> None:
    factory, make_client = env
    async with make_client() as client:
        await attempt(client, "someone@example.com", "wrong-password-1")
    async with factory() as db:
        rows = (await db.execute(select(RateLimitEvent))).scalars().all()
        assert rows and all("someone" not in row.key and "127.0.0.1" not in row.key and len(row.key) == 64 for row in rows)
        db.add(RateLimitEvent(scope="login_email", key="x" * 64, created_at=datetime.now(timezone.utc) - timedelta(days=3)))
        await db.commit()
    assert await rate_limit_service.purge_old_events(factory) == 1
