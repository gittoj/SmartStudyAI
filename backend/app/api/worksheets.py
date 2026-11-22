import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status

from app.core.deps import CurrentParent, Db, get_owned_child
from app.models import Child, Worksheet
from app.schemas import Subject, WorksheetStatusResponse
from app.services import worksheet_service
from app.services.document_service import UploadRejected, validate_upload

router = APIRouter(prefix="/api/worksheets", tags=["worksheets"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_worksheet(
    parent: CurrentParent, db: Db, background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    child_id: Annotated[uuid.UUID, Form(alias="childId")],
    subject: Annotated[Subject, Form()],
    topic_hint: Annotated[str | None, Form(alias="topicHint", max_length=120)] = None,
) -> dict[str, str]:
    """Parent only. Validation failures store nothing and call no external service."""
    child = await get_owned_child(child_id, db, parent)
    data = await file.read(10 * 1024 * 1024 + 1)
    try:
        validate_upload(file.filename or "", data)
        worksheet_id = await worksheet_service.create_worksheet(
            db, child, subject, topic_hint, file.filename or "", data)
    except UploadRejected as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    background.add_task(worksheet_service.process_worksheet, worksheet_id)
    return {"id": str(worksheet_id)}


@router.get("/{worksheet_id}", response_model=WorksheetStatusResponse)
async def get_worksheet_status(worksheet_id: uuid.UUID, parent: CurrentParent, db: Db) -> WorksheetStatusResponse:
    """Parent polling for upload progress and the message to show."""
    worksheet = await db.get(Worksheet, worksheet_id)
    child = await db.get(Child, worksheet.child_id) if worksheet else None
    if worksheet is None or child is None or child.parent_id != parent.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That worksheet could not be found.")
    return WorksheetStatusResponse(
        id=worksheet.id, status=worksheet.status, parent_note=worksheet.parent_note,
        failure_reason=worksheet.failure_reason,
        can_retry=worksheet.status == "failed" and worksheet.retry_count == 0 and worksheet.storage_key is not None,
    )


@router.post("/{worksheet_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_worksheet(worksheet_id: uuid.UUID, parent: CurrentParent, db: Db, background: BackgroundTasks) -> dict[str, str]:
    await worksheet_service.retry_worksheet(db, parent, worksheet_id)
    background.add_task(worksheet_service.process_worksheet, worksheet_id)
    return {"id": str(worksheet_id)}


@router.delete("/{worksheet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_worksheet(worksheet_id: uuid.UUID, parent: CurrentParent, db: Db) -> None:
    """Remove a failed or needs_review worksheet and its stored file."""
    await worksheet_service.remove_worksheet(db, parent, worksheet_id)
