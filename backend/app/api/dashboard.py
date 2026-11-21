from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentParent, Db, OwnedChild
from app.schemas import ParentDashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/{child_id}", response_model=ParentDashboard)
async def get_dashboard(child: OwnedChild, parent: CurrentParent, db: Db) -> ParentDashboard:
    """TODO: read saved TopicProgress (sorted subject, then needs_practice > developing >
    confident > not_started) plus newest 8 worksheets. Uploaded topics with no attempts show
    not_started. Never call OpenAI/PyMuPDF/OCR here."""
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Not built yet.")
