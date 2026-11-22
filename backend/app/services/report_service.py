import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Attempt, Question, QuestionReport, Worksheet
from app.schemas import ReportedQuestion
from app.services.analytics_service import refresh_topic_progress


async def report_question(db, child, question_id: uuid.UUID, reason: str) -> None:
    """A child flags a question they have already answered. Repeating it changes nothing."""
    question = await db.get(Question, question_id)
    worksheet = await db.get(Worksheet, question.worksheet_id) if question else None
    if question is None or worksheet is None or worksheet.child_id != child.id:
        raise HTTPException(404, "That question could not be found.")
    answered = (await db.execute(select(Attempt.id).where(
        Attempt.child_id == child.id, Attempt.question_id == question.id))).first()
    if answered is None:  # the answer is only revealed after answering, and the form lives on that screen
        raise HTTPException(409, "Answer the question first.")
    existing = (await db.execute(select(QuestionReport.id).where(
        QuestionReport.child_id == child.id, QuestionReport.question_id == question.id))).first()
    if existing:
        return
    db.add(QuestionReport(child_id=child.id, question_id=question.id, worksheet_id=worksheet.id, reason=reason))
    try:
        await db.flush()
    except IntegrityError:  # double click
        await db.rollback()
        return
    await refresh_topic_progress(db, child.id, worksheet.subject, worksheet.level, worksheet.topic)
    await db.commit()


async def open_reports(db, child_id: uuid.UUID) -> list[ReportedQuestion]:
    rows = (await db.execute(
        select(QuestionReport, Question, Worksheet)
        .join(Question, Question.id == QuestionReport.question_id)
        .join(Worksheet, Worksheet.id == QuestionReport.worksheet_id)
        .where(QuestionReport.child_id == child_id, QuestionReport.status == "open")
        .order_by(QuestionReport.created_at.desc()))).all()
    return [ReportedQuestion(
        id=report.id, topic=worksheet.topic, prompt=question.prompt, choices=question.choices,
        correct_choice=question.expected_answer, explanation=question.explanation,
        reason=report.reason, created_at=report.created_at) for report, question, worksheet in rows]


async def resolve_report(db, child, report_id: uuid.UUID, resolution: str) -> None:
    report = await db.get(QuestionReport, report_id)
    if report is None or report.child_id != child.id:
        raise HTTPException(404, "That report could not be found.")
    if report.status != "open":
        return
    report.status = resolution
    worksheet = await db.get(Worksheet, report.worksheet_id)
    await refresh_topic_progress(db, child.id, worksheet.subject, worksheet.level, worksheet.topic)
    await db.commit()
