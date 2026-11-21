import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentChild, Db
from app.models import Question, Worksheet
from app.schemas import PracticeFeedback, SubmitAnswerRequest, WorksheetResult, WorksheetSummary
from app.services import exercise_service

router = APIRouter(prefix="/api/practice", tags=["practice"])


@router.get("/worksheets", response_model=list[WorksheetSummary])
async def list_ready_worksheets(child: CurrentChild, db: Db) -> list[Worksheet]:
    """Child sees ready worksheets only."""
    rows = await db.execute(select(Worksheet).where(Worksheet.child_id == child.id, Worksheet.status == "ready"))
    return list(rows.scalars())


@router.get("/worksheets/{worksheet_id}", response_model=WorksheetResult)
async def get_practice_worksheet(worksheet_id: uuid.UUID, child: CurrentChild, db: Db) -> WorksheetResult:
    """TODO: load worksheet (must belong to child, status ready; processing -> 409 'Your worksheet is
    being prepared'), map Question rows to PracticeQuestion WITHOUT expected_answer/explanation."""
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Not built yet.")


@router.post("/questions/{question_id}/answer", response_model=PracticeFeedback)
async def submit_practice_answer(question_id: uuid.UUID, body: SubmitAnswerRequest, child: CurrentChild, db: Db) -> PracticeFeedback:
    return await exercise_service.submit_practice_answer(db, child, question_id, body.answer)
