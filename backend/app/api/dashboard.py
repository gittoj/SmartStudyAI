import uuid

from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.core.deps import Db, OwnedChild
from app.models import TopicProgress as TopicProgressRow
from app.models import Worksheet
from app.schemas import DashboardChild, DashboardWorksheet, ParentDashboard, ResolveReportRequest, TopicProgress
from app.services import report_service
from app.services.analytics_service import MASTERY_ORDER

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
RECENT_WORKSHEET_LIMIT = 8


@router.get("/{child_id}", response_model=ParentDashboard)
async def get_dashboard(child: OwnedChild, db: Db) -> ParentDashboard:
    """Read-only, from saved records. OwnedChild guarantees the child belongs to the logged-in parent.
    Topics: grouped by subject, then needs_practice, developing, confident, not_started.
    Never calls OpenAI, PyMuPDF or OCR."""
    rank = {mastery: index for index, mastery in enumerate(MASTERY_ORDER)}
    rows = (await db.execute(select(TopicProgressRow).where(TopicProgressRow.child_id == child.id))).scalars().all()
    rows.sort(key=lambda row: (row.subject, rank[row.mastery], row.topic))
    worksheets = (await db.execute(
        select(Worksheet).where(Worksheet.child_id == child.id)
        .order_by(Worksheet.created_at.desc()).limit(RECENT_WORKSHEET_LIMIT))).scalars().all()
    return ParentDashboard(
        child=DashboardChild.model_validate(child),
        topics=[TopicProgress.model_validate(row) for row in rows],
        recent_worksheets=[DashboardWorksheet.model_validate(w) for w in worksheets],
        reported_questions=await report_service.open_reports(db, child.id),
    )


@router.post("/{child_id}/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def resolve_report(report_id: uuid.UUID, body: ResolveReportRequest, child: OwnedChild, db: Db) -> Response:
    """Parent decides: confirmed = the question is wrong (stays hidden from progress),
    dismissed = it is fine (counts again). OwnedChild keeps other parents out."""
    await report_service.resolve_report(db, child, report_id, body.resolution)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
