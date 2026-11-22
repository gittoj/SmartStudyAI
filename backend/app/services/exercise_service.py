import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Attempt, Question, Worksheet
from app.schemas import PracticeFeedback
from app.services.analytics_service import refresh_topic_progress


def build_feedback(is_correct: bool, chosen: str, explanation: str) -> str:
    """Generated server-side from the stored key. No OpenAI call, no 'wrong', no scores."""
    if is_correct:
        return f"You chose {chosen}. {explanation}"
    return f"Let's look at this again. {explanation}"


async def _find_attempt(db, child_id: uuid.UUID, question_id: uuid.UUID) -> Attempt | None:
    return (await db.execute(
        select(Attempt).where(Attempt.child_id == child_id, Attempt.question_id == question_id)
    )).scalar_one_or_none()


async def submit_practice_answer(db, child, question_id: uuid.UUID, answer: str) -> PracticeFeedback:
    """Check server-side. One submission per question; a repeat returns the stored feedback
    and leaves progress unchanged. Progress is refreshed in the same transaction."""
    question = await db.get(Question, question_id)
    worksheet = await db.get(Worksheet, question.worksheet_id) if question else None
    if question is None or worksheet is None or worksheet.child_id != child.id or worksheet.status != "ready":
        raise HTTPException(404, "That question could not be found.")
    correct_choice, explanation = question.expected_answer, question.explanation

    existing = await _find_attempt(db, child.id, question.id)
    if existing:
        return _to_feedback(existing, correct_choice, explanation)
    if answer not in question.choices:
        raise HTTPException(422, "Choose an answer first.")

    is_correct = answer == correct_choice
    attempt = Attempt(
        child_id=child.id, worksheet_id=worksheet.id, question_id=question.id, answer=answer,
        is_correct=is_correct, feedback=build_feedback(is_correct, answer, explanation),
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    try:
        await db.flush()
    except IntegrityError:  # double-click race: another request stored this attempt first
        await db.rollback()
        stored = await _find_attempt(db, child.id, question_id)
        return _to_feedback(stored, correct_choice, explanation)
    await refresh_topic_progress(db, child.id, worksheet.subject, worksheet.level, worksheet.topic)
    await db.commit()
    return _to_feedback(attempt, correct_choice, explanation)


def _to_feedback(attempt: Attempt, correct_choice: str, explanation: str) -> PracticeFeedback:
    return PracticeFeedback(
        id=attempt.id, question_id=attempt.question_id, is_correct=attempt.is_correct,
        correct_choice=correct_choice, explanation=explanation,
        feedback=attempt.feedback, submitted_at=attempt.submitted_at,
    )
