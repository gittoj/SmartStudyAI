import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select

from app.models import Attempt, Question, Worksheet
from app.schemas import PracticeFeedback


def build_feedback(is_correct: bool, chosen: str, explanation: str) -> str:
    """Generated server-side from the stored key. No OpenAI call, no 'wrong', no scores."""
    if is_correct:
        return f"You chose {chosen}. {explanation}"
    return f"Let's look at this again. {explanation}"


async def submit_practice_answer(db, child, question_id: uuid.UUID, answer: str) -> PracticeFeedback:
    """Check server-side. One submission per question; repeat returns stored feedback unchanged."""
    question = await db.get(Question, question_id)
    worksheet = await db.get(Worksheet, question.worksheet_id) if question else None
    if question is None or worksheet is None or worksheet.child_id != child.id or worksheet.status != "ready":
        raise HTTPException(404, "That question could not be found.")

    existing = (await db.execute(
        select(Attempt).where(Attempt.child_id == child.id, Attempt.question_id == question.id)
    )).scalar_one_or_none()
    if existing:
        return _to_feedback(existing, question)

    if answer not in question.choices:
        raise HTTPException(422, "Choose an answer first.")

    is_correct = answer == question.expected_answer
    attempt = Attempt(
        child_id=child.id, worksheet_id=worksheet.id, question_id=question.id, answer=answer,
        is_correct=is_correct, feedback=build_feedback(is_correct, answer, question.explanation),
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    await db.flush()
    # TODO: await analytics_service.refresh_topic_progress(db, child.id, worksheet.subject, worksheet.level, worksheet.topic)
    await db.commit()
    return _to_feedback(attempt, question)


def _to_feedback(attempt: Attempt, question: Question) -> PracticeFeedback:
    return PracticeFeedback(
        id=attempt.id, question_id=question.id, is_correct=attempt.is_correct,
        correct_choice=question.expected_answer, explanation=question.explanation,
        feedback=attempt.feedback, submitted_at=attempt.submitted_at,
    )
