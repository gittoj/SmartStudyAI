import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import Base, Question, TopicProgress, Worksheet

SECRET = "SECRET-EXPLANATION"
PASSWORD = "a-long-password-123"


@pytest.fixture
async def env(monkeypatch):
    monkeypatch.setattr(settings, "cookie_secure", False)
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    yield factory, lambda: AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()
    await engine.dispose()


async def register_and_login(client, email="p@example.com") -> None:
    body = {"email": email, "displayName": "P", "password": PASSWORD}
    assert (await client.post("/api/auth/register", json=body)).status_code == 201
    assert (await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})).status_code == 200


async def create_child(client, username="alex") -> str:
    response = await client.post("/api/children", json={"username": username, "level": "P3", "pin": "1234"})
    assert response.status_code == 201
    return response.json()["id"]


async def child_login(client, child_id: str) -> None:
    assert (await client.post(f"/api/children/{child_id}/select", json={"pin": "1234"})).status_code == 200


async def seed_worksheet(factory, child_id: str, *, status="ready", topic="fractions", created_at=None, note=""):
    async with factory() as db:
        worksheet = Worksheet(
            child_id=uuid.UUID(child_id), subject="mathematics", level="P3", topic=topic, status=status,
            explanation="Halves.", worked_example={"prompt": "p", "steps": ["s"], "answer": "a"},
            parent_note=note, created_at=created_at or datetime.now(timezone.utc))
        db.add(worksheet)
        await db.flush()
        question_ids: list[str] = []
        if status == "ready":
            for position in range(1, 6):
                question = Question(worksheet_id=worksheet.id, position=position, prompt=f"Q{position}?",
                                    choices=["1", "2", "3", "4"], expected_answer="2", explanation=SECRET)
                db.add(question)
                await db.flush()
                question_ids.append(str(question.id))
            db.add(TopicProgress(child_id=uuid.UUID(child_id), subject="mathematics", level="P3", topic=topic))
        await db.commit()
        return str(worksheet.id), question_ids


async def seed_progress(factory, child_id: str, topic: str, mastery: str) -> None:
    async with factory() as db:
        db.add(TopicProgress(child_id=uuid.UUID(child_id), subject="mathematics", level="P3",
                             topic=topic, mastery=mastery))
        await db.commit()


async def test_child_reads_ready_worksheet_without_answer_key(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        await register_and_login(client)
        child_id = await create_child(client)
        worksheet_id, _ = await seed_worksheet(factory, child_id)
        await child_login(client, child_id)
        response = await client.get(f"/api/practice/worksheets/{worksheet_id}")
        assert response.status_code == 200
        body = response.json()
        assert len(body["practiceQuestions"]) == 5
        assert set(body["practiceQuestions"][0]) == {"id", "prompt", "choices"}
        assert "expectedAnswer" not in response.text and SECRET not in response.text


async def test_processing_worksheet_says_being_prepared(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        await register_and_login(client)
        child_id = await create_child(client)
        worksheet_id, _ = await seed_worksheet(factory, child_id, status="processing")
        await child_login(client, child_id)
        response = await client.get(f"/api/practice/worksheets/{worksheet_id}")
        assert response.status_code == 409 and "being prepared" in response.json()["detail"]


async def test_broken_worksheet_is_hidden_from_child(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        await register_and_login(client)
        child_id = await create_child(client)
        worksheet_id, _ = await seed_worksheet(factory, child_id, status="needs_review")
        await child_login(client, child_id)
        assert (await client.get(f"/api/practice/worksheets/{worksheet_id}")).status_code == 404


async def test_child_cannot_open_a_siblings_worksheet(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        await register_and_login(client)
        first = await create_child(client, "alex")
        second = await create_child(client, "sam")
        worksheet_id, question_ids = await seed_worksheet(factory, second)
        await child_login(client, first)
        assert (await client.get(f"/api/practice/worksheets/{worksheet_id}")).status_code == 404
        answer = await client.post(f"/api/practice/questions/{question_ids[0]}/answer", json={"answer": "2"})
        assert answer.status_code == 404


async def test_answers_update_progress_and_dashboard(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        await register_and_login(client)
        child_id = await create_child(client)
        _, questions = await seed_worksheet(factory, child_id)
        await child_login(client, child_id)

        right = await client.post(f"/api/practice/questions/{questions[0]}/answer", json={"answer": "2"})
        assert right.status_code == 200 and right.json()["isCorrect"] is True
        wrong = await client.post(f"/api/practice/questions/{questions[1]}/answer", json={"answer": "1"})
        assert wrong.json()["isCorrect"] is False and wrong.json()["correctChoice"] == "2"
        repeat = await client.post(f"/api/practice/questions/{questions[0]}/answer", json={"answer": "3"})
        assert repeat.json()["isCorrect"] is True  # stored feedback; progress unchanged
        invalid = await client.post(f"/api/practice/questions/{questions[2]}/answer", json={"answer": "99"})
        assert invalid.status_code == 422 and invalid.json()["detail"] == "Choose an answer first."

        dashboard = await client.get(f"/api/dashboard/{child_id}")
        assert dashboard.status_code == 200
        topic = dashboard.json()["topics"][0]
        assert (topic["questionsAttempted"], topic["questionsCorrect"]) == (2, 1)
        assert topic["mastery"] == "developing" and topic["lastPractisedAt"] is not None


async def test_dashboard_orders_topics_and_shows_recent_eight(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        await register_and_login(client)
        child_id = await create_child(client)
        for topic, mastery in [("a", "confident"), ("b", "needs_practice"), ("c", "not_started"), ("d", "developing")]:
            await seed_progress(factory, child_id, topic, mastery)
        start = datetime.now(timezone.utc)
        for index in range(9):
            await seed_worksheet(factory, child_id, status="needs_review", topic="",
                                 created_at=start + timedelta(minutes=index), note=f"note {index}")
        body = (await client.get(f"/api/dashboard/{child_id}")).json()
        assert [t["topic"] for t in body["topics"]] == ["b", "d", "a", "c"]
        assert len(body["recentWorksheets"]) == 8
        assert body["recentWorksheets"][0]["parentNote"] == "note 8"  # newest first
        assert body["child"] == {"id": child_id, "username": "alex", "level": "P3"}


async def test_dashboard_requires_the_parent_session(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        await register_and_login(client)
        child_id = await create_child(client)
        await child_login(client, child_id)
        client.cookies.delete("parent_session")  # only the child session remains
        assert (await client.get(f"/api/dashboard/{child_id}")).status_code == 401


async def test_another_parent_cannot_read_a_child_or_worksheet(env) -> None:
    factory, make_client = env
    async with make_client() as owner, make_client() as stranger:
        await register_and_login(owner, "owner@example.com")
        child_id = await create_child(owner)
        worksheet_id, _ = await seed_worksheet(factory, child_id)
        await register_and_login(stranger, "stranger@example.com")
        assert (await stranger.get(f"/api/dashboard/{child_id}")).status_code == 404
        assert (await stranger.get(f"/api/worksheets/{worksheet_id}")).status_code == 404
        assert (await stranger.post(f"/api/children/{child_id}/select", json={"pin": "1234"})).status_code == 404


async def test_cors_allows_the_frontend_origin_with_cookies(env) -> None:
    _, make_client = env
    async with make_client() as client:
        response = await client.options("/api/auth/login", headers={
            "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"})
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert response.headers["access-control-allow-credentials"] == "true"
