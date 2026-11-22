"""Upload -> read -> generate pipeline.
Status flow: uploaded -> processing -> ready | needs_review | failed.
Expected outcomes (unreadable, wrong subject, ready) are written by _run_pipeline.
Any other exception (OCR down, OpenAI failure/timeout, bug) becomes `failed`.
Logs contain worksheet id, status and error code only."""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Child, Parent, Question, TopicProgress, Worksheet
from app.services.ai_service import GenerationFailed, generate_worksheet, subject_mismatch
from app.services.document_service import (
    ExtractedPage, OcrUnavailable, UploadRejected, detect_mime, extract_pages, is_readable, readable_text,
)
from app.services.storage_service import delete_file, new_storage_key, read_file, save_file

logger = logging.getLogger(__name__)

UNREADABLE_MESSAGE = "We could not read this clearly. Upload a brighter, flatter photo."
FAILED_MESSAGE = "We could not prepare this worksheet. Try again."
TOO_MANY_MESSAGE = "Please wait. This child already has worksheets being read."
MAX_IN_PROGRESS_PER_CHILD = 20
MAX_CONCURRENT_PER_PARENT = 2
SUBJECT_LABEL = {"mathematics": "Mathematics", "english": "English"}

# In-process limit. With several API workers, replace with a DB or queue-based limit.
_parent_slots: dict[uuid.UUID, asyncio.Semaphore] = {}


def _slot(parent_id: uuid.UUID) -> asyncio.Semaphore:
    return _parent_slots.setdefault(parent_id, asyncio.Semaphore(MAX_CONCURRENT_PER_PARENT))


def normalise_topic(topic: str) -> str:
    """One consistent topic name per subject + concept (lowercase, collapsed whitespace)."""
    return " ".join(topic.lower().split())


async def create_worksheet(db, child: Child, subject: str, topic_hint: str | None, file_name: str, data: bytes) -> uuid.UUID:
    """Caller has already run validate_upload. Checks the in-progress cap, stores the file
    privately (key only in the DB) and inserts the row with status `uploaded`."""
    in_progress = (await db.execute(
        select(func.count()).select_from(Worksheet).where(
            Worksheet.child_id == child.id, Worksheet.status.in_(("uploaded", "processing")))
    )).scalar_one()
    if in_progress >= MAX_IN_PROGRESS_PER_CHILD:
        raise UploadRejected(TOO_MANY_MESSAGE)
    extension = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    key = new_storage_key(child.id, extension)
    await save_file(key, data)
    worksheet = Worksheet(
        child_id=child.id, subject=subject, level=child.level, status="uploaded",
        storage_key=key, topic_hint=(topic_hint or "").strip() or None,
    )
    db.add(worksheet)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        await delete_file(key)
        raise
    return worksheet.id


async def process_worksheet(worksheet_id: uuid.UUID, session_factory=SessionLocal) -> None:
    """Background task. Uses its own DB session because the request session is closed by now."""
    async with session_factory() as db:
        worksheet = await db.get(Worksheet, worksheet_id)
        if worksheet is None or worksheet.status != "uploaded":
            return
        child = await db.get(Child, worksheet.child_id)
        worksheet.status = "processing"
        await db.commit()
        try:
            async with _slot(child.parent_id):
                await asyncio.wait_for(_run_pipeline(db, worksheet_id, child), timeout=settings.processing_timeout_seconds)
        except Exception as error:  # includes TimeoutError, GenerationFailed, OcrUnavailable
            await db.rollback()
            await _mark_failed(db, worksheet_id, "service_unavailable")
            # Our own error codes carry no worksheet content, so the reason is safe to log.
            reason = str(error) if isinstance(error, (GenerationFailed, OcrUnavailable)) else ""
            logger.error("worksheet=%s status=failed error=%s reason=%s", worksheet_id, type(error).__name__, reason)


async def _run_pipeline(db, worksheet_id: uuid.UUID, child: Child) -> None:
    worksheet = await db.get(Worksheet, worksheet_id)

    # 1. Read. On a retry, reuse stored text; only re-extract if extraction itself failed.
    if worksheet.extracted_pages is None:
        data = await read_file(worksheet.storage_key)
        pages = await extract_pages(data, detect_mime(data) or "")
        if not is_readable(pages):
            await _mark_needs_review(db, worksheet_id, "unreadable", UNREADABLE_MESSAGE)
            return
        worksheet.extracted_pages = [
            {"pageNumber": p.page_number, "text": p.text, "confidence": p.confidence} for p in pages
        ]
        await db.commit()
    else:
        pages = [ExtractedPage(p["pageNumber"], p["text"], p["confidence"]) for p in worksheet.extracted_pages]
    text = readable_text(pages)

    # 2. Generate (one OpenAI call, 60s timeout inside generate_worksheet).
    existing_topics = list((await db.execute(
        select(TopicProgress.topic).where(
            TopicProgress.child_id == worksheet.child_id,
            TopicProgress.subject == worksheet.subject, TopicProgress.level == worksheet.level)
    )).scalars())
    generated = await generate_worksheet(worksheet.subject, worksheet.level, worksheet.topic_hint, text, existing_topics)

    # 3. Subject mismatch: no practice for the child.
    if subject_mismatch(generated, worksheet.subject):
        message = (f"This looks like {SUBJECT_LABEL[generated.detected_subject]}, but it was uploaded as "
                   f"{SUBJECT_LABEL[worksheet.subject]}. Change the subject or upload a different page.")
        await _mark_needs_review(db, worksheet_id, "wrong_subject", message)
        return

    # 4. Save result + AnswerKey; make sure the topic shows up on the dashboard as not_started.
    topic = normalise_topic(generated.topic)
    worksheet.topic = topic
    worksheet.explanation = generated.explanation
    worksheet.worked_example = generated.worked_example.model_dump()  # type: ignore[union-attr]
    worksheet.parent_note = generated.parent_note
    for position, question in enumerate(generated.questions, start=1):
        db.add(Question(worksheet_id=worksheet.id, position=position, prompt=question.prompt,
                        choices=question.choices, expected_answer=question.expected_answer,
                        explanation=question.explanation))
    exists = (await db.execute(select(TopicProgress.id).where(
        TopicProgress.child_id == worksheet.child_id, TopicProgress.subject == worksheet.subject,
        TopicProgress.topic == topic))).first()
    if exists is None:
        db.add(TopicProgress(child_id=worksheet.child_id, subject=worksheet.subject,
                             level=worksheet.level, topic=topic))
    worksheet.extracted_pages = None  # no longer needed once ready
    worksheet.failure_reason = None
    worksheet.status = "ready"
    await db.commit()
    logger.info("worksheet=%s status=ready", worksheet_id)


async def _mark_failed(db, worksheet_id: uuid.UUID, reason: str) -> None:
    worksheet = await db.get(Worksheet, worksheet_id)
    worksheet.status = "failed"
    worksheet.failure_reason = reason
    worksheet.parent_note = FAILED_MESSAGE
    if worksheet.retry_count >= 1:
        worksheet.extracted_pages = None  # retry used up; drop the text, file stays 7 days
    await db.commit()


async def _mark_needs_review(db, worksheet_id: uuid.UUID, reason: str, message: str) -> None:
    worksheet = await db.get(Worksheet, worksheet_id)
    worksheet.status = "needs_review"
    worksheet.failure_reason = reason
    worksheet.parent_note = message
    worksheet.extracted_pages = None
    await db.commit()
    logger.info("worksheet=%s status=needs_review error=%s", worksheet_id, reason)


async def retry_worksheet(db, parent: Parent, worksheet_id: uuid.UUID) -> None:
    """Exactly one manual retry, from the same stored file. The caller schedules process_worksheet."""
    worksheet = await db.get(Worksheet, worksheet_id)
    child = await db.get(Child, worksheet.child_id) if worksheet else None
    if worksheet is None or child is None or child.parent_id != parent.id:
        raise HTTPException(404, "That worksheet could not be found.")
    if worksheet.status != "failed" or worksheet.retry_count >= 1 or worksheet.storage_key is None:
        raise HTTPException(409, "This worksheet can't be tried again. Upload it again instead.")
    worksheet.retry_count = 1
    worksheet.failure_reason = None
    worksheet.status = "uploaded"
    worksheet.queued_at = datetime.now(timezone.utc)  # restart the stuck-job clock
    await db.commit()


async def purge_expired_files(session_factory=SessionLocal) -> int:
    """Delete originals of failed / needs_review worksheets older than the retention window.
    Uses created_at as a close proxy for the time of failure."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.failed_file_retention_days)
    purged = 0
    async with session_factory() as db:
        rows = await db.execute(select(Worksheet).where(
            Worksheet.status.in_(("failed", "needs_review")),
            Worksheet.created_at < cutoff, Worksheet.storage_key.is_not(None)))
        for worksheet in rows.scalars():
            await delete_file(worksheet.storage_key)
            worksheet.storage_key = None
            worksheet.extracted_pages = None
            purged += 1
        await db.commit()
    return purged


async def remove_worksheet(db, parent: Parent, worksheet_id: uuid.UUID) -> None:
    """Parent removes a worksheet that could not be prepared (failed or needs_review).
    Ready worksheets are not removable: that would erase the child's practice history."""
    worksheet = await db.get(Worksheet, worksheet_id)
    child = await db.get(Child, worksheet.child_id) if worksheet else None
    if worksheet is None or child is None or child.parent_id != parent.id:
        raise HTTPException(404, "That worksheet could not be found.")
    if worksheet.status not in ("failed", "needs_review"):
        raise HTTPException(409, "Only worksheets that could not be prepared can be removed.")
    key = worksheet.storage_key
    await db.delete(worksheet)
    await db.commit()
    if key:
        try:
            await delete_file(key)
        except OSError as error:  # the row is gone; a leftover file is logged, not shown to the parent
            logger.error("worksheet=%s file_delete_failed error=%s", worksheet_id, type(error).__name__)


async def recover_stuck_worksheets(session_factory=SessionLocal, now: datetime | None = None) -> int:
    """Mark worksheets that have been `uploaded` or `processing` for too long as `failed`.

    A server restart or crash mid-job leaves a row in progress forever. After
    settings.stuck_worksheet_minutes it becomes `failed` with the standard message, so the parent
    can retry once (if no retry was used) or remove it. Returns how many rows were recovered.
    """
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(minutes=settings.stuck_worksheet_minutes)
    async with session_factory() as db:
        rows = (await db.execute(select(Worksheet).where(
            Worksheet.status.in_(("uploaded", "processing")),
            func.coalesce(Worksheet.queued_at, Worksheet.created_at) < cutoff,
        ))).scalars().all()
        for worksheet in rows:
            worksheet.status = "failed"
            worksheet.failure_reason = "service_unavailable"
            worksheet.parent_note = FAILED_MESSAGE
            if worksheet.retry_count >= 1:
                worksheet.extracted_pages = None  # retry already used; keep the file for the 7-day window only
            logger.error("worksheet=%s status=failed error=stuck_recovered", worksheet.id)
        await db.commit()
    return len(rows)
