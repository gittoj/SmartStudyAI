import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentChild, Db
from app.models import Question, Worksheet
from app.schemas import (
    DashboardChild, PracticeFeedback, PracticeQuestion, SubmitAnswerRequest, WorkedExample, WorksheetResult, WorksheetSummary,
)
from app.services import exercise_service

router = APIRouter(prefix="/api/practice", tags=["practice"])


@router.get("/me", response_model=DashboardChild)
async def get_selected_child(child: CurrentChild) -> DashboardChild:
    """Who is practising? Also tells the frontend whether a child session exists (401 if not)."""
    return DashboardChild.model_validate(child)


@router.get("/worksheets", response_model=list[WorksheetSummary])
async def list_ready_worksheets(child: CurrentChild, db: Db) -> list[Worksheet]:
    """Child sees their own ready worksheets only, newest first."""
    rows = await db.execute(
        select(Worksheet).where(Worksheet.child_id == child.id, Worksheet.status == "ready")
        .order_by(Worksheet.created_at.desc()))
    return list(rows.scalars())


@router.get("/worksheets/{worksheet_id}", response_model=WorksheetResult)
async def get_practice_worksheet(worksheet_id: uuid.UUID, child: CurrentChild, db: Db) -> WorksheetResult:
    """Explanation, worked example and questions for the selected child. Never includes the
    answer key. Worksheets that are not ready are not shown as results to the child."""
    worksheet = await db.get(Worksheet, worksheet_id)
    if worksheet is None or worksheet.child_id != child.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That worksheet could not be found.")
    if worksheet.status in ("uploaded", "processing"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Your worksheet is being prepared")
    if worksheet.status != "ready":  # needs_review / failed: the child never sees the broken result
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That worksheet could not be found.")
    questions = (await db.execute(
        select(Question).where(Question.worksheet_id == worksheet.id).order_by(Question.position))).scalars().all()
    return WorksheetResult(
        id=worksheet.id, child_id=worksheet.child_id, subject=worksheet.subject, level=worksheet.level,
        topic=worksheet.topic, status=worksheet.status, explanation=worksheet.explanation,
        worked_example=WorkedExample.model_validate(worksheet.worked_example) if worksheet.worked_example else None,
        practice_questions=[PracticeQuestion(id=q.id, prompt=q.prompt, choices=q.choices) for q in questions],
        parent_note="",  # parent-facing; not shown to the child
        created_at=worksheet.created_at,
    )


@router.post("/questions/{question_id}/answer", response_model=PracticeFeedback)
async def submit_practice_answer(question_id: uuid.UUID, body: SubmitAnswerRequest, child: CurrentChild, db: Db) -> PracticeFeedback:
    return await exercise_service.submit_practice_answer(db, child, question_id, body.answer)
