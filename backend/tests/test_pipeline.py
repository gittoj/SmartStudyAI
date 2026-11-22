import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base, Child, Parent, Question, TopicProgress, Worksheet
from app.schemas import GeneratedQuestion, GeneratedWorksheet, WorkedExample
from app.services import worksheet_service as service
from app.services.ai_service import GenerationFailed
from app.services.document_service import ExtractedPage


def _generated(subject: str = "mathematics") -> GeneratedWorksheet:
    if subject != "mathematics":
        return GeneratedWorksheet(detected_subject=subject)
    question = GeneratedQuestion(prompt="Q?", choices=["1", "2", "3", "4"], expected_answer="2", explanation="Two.")
    return GeneratedWorksheet(
        detected_subject="mathematics", topic="  Fractions  Of A Set ", explanation="Halves.",
        worked_example=WorkedExample(prompt="p", steps=["s"], answer="a"), parent_note="note",
        questions=[question] * 5,
    )


@pytest.fixture
async def factory():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def seeded(factory):
    async with factory() as db:
        parent = Parent(email="p@example.com", display_name="P", password_hash="x")
        db.add(parent)
        await db.flush()
        child = Child(parent_id=parent.id, username="alex", level="P3", pin_hash="x")
        db.add(child)
        await db.flush()
        worksheet = Worksheet(child_id=child.id, subject="mathematics", level="P3", storage_key="k.png")
        db.add(worksheet)
        await db.commit()
        return parent, worksheet.id


@pytest.fixture
def calls(monkeypatch):
    state = {"extract": 0, "generate": 0, "pages": [ExtractedPage(1, "Shade half of the shapes. " * 3, 0.9)],
             "result": _generated()}

    async def fake_read(_key): return b"\x89PNG\r\n\x1a\n"

    async def fake_extract(_data, _mime):
        state["extract"] += 1
        return state["pages"]

    async def fake_generate(*_args):
        state["generate"] += 1
        if isinstance(state["result"], Exception):
            raise state["result"]
        return state["result"]

    monkeypatch.setattr(service, "read_file", fake_read)
    monkeypatch.setattr(service, "extract_pages", fake_extract)
    monkeypatch.setattr(service, "generate_worksheet", fake_generate)
    return state


async def _status(factory, worksheet_id):
    async with factory() as db:
        return await db.get(Worksheet, worksheet_id)


async def test_unreadable_skips_openai(factory, seeded, calls) -> None:
    calls["pages"] = [ExtractedPage(1, "blur", 0.2)]
    await service.process_worksheet(seeded[1], factory)
    worksheet = await _status(factory, seeded[1])
    assert worksheet.status == "needs_review" and worksheet.parent_note == service.UNREADABLE_MESSAGE
    assert calls["generate"] == 0


async def test_wrong_subject_needs_review_without_questions(factory, seeded, calls) -> None:
    calls["result"] = _generated("english")
    await service.process_worksheet(seeded[1], factory)
    worksheet = await _status(factory, seeded[1])
    assert worksheet.status == "needs_review" and "looks like English" in worksheet.parent_note
    async with factory() as db:
        assert (await db.execute(select(Question))).first() is None


async def test_success_saves_questions_topic_and_clears_text(factory, seeded, calls) -> None:
    await service.process_worksheet(seeded[1], factory)
    worksheet = await _status(factory, seeded[1])
    assert worksheet.status == "ready" and worksheet.topic == "fractions of a set"
    assert worksheet.extracted_pages is None
    async with factory() as db:
        assert len((await db.execute(select(Question))).scalars().all()) == 5
        progress = (await db.execute(select(TopicProgress))).scalar_one()
        assert progress.mastery == "not_started"


async def test_failure_then_single_retry_reuses_extracted_text(factory, seeded, calls) -> None:
    parent, worksheet_id = seeded
    calls["result"] = GenerationFailed("timeout")
    await service.process_worksheet(worksheet_id, factory)
    worksheet = await _status(factory, worksheet_id)
    assert worksheet.status == "failed" and worksheet.parent_note == service.FAILED_MESSAGE
    assert worksheet.extracted_pages is not None

    async with factory() as db:
        await service.retry_worksheet(db, parent, worksheet_id)
    await service.process_worksheet(worksheet_id, factory)
    assert calls["extract"] == 1  # text reused, file not re-read
    worksheet = await _status(factory, worksheet_id)
    assert worksheet.status == "failed" and worksheet.extracted_pages is None

    async with factory() as db:
        with pytest.raises(HTTPException) as caught:
            await service.retry_worksheet(db, parent, worksheet_id)
    assert caught.value.status_code == 409


async def test_retry_refused_for_another_parent(factory, seeded) -> None:
    _, worksheet_id = seeded
    async with factory() as db:
        stranger = Parent(email="s@example.com", display_name="S", password_hash="x")
        db.add(stranger)
        await db.flush()
        with pytest.raises(HTTPException) as caught:
            await service.retry_worksheet(db, stranger, worksheet_id)
    assert caught.value.status_code == 404
