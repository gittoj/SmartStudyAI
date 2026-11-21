import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status

from app.core.deps import CurrentParent, Db, get_owned_child
from app.schemas import Subject
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
    except UploadRejected as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    worksheet_id = await worksheet_service.create_worksheet(
        db, parent, child, subject, topic_hint, file.filename or "", data
    )
    background.add_task(worksheet_service.process_worksheet, worksheet_id)
    return {"id": str(worksheet_id)}


@router.post("/{worksheet_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_worksheet(worksheet_id: uuid.UUID, parent: CurrentParent, db: Db, background: BackgroundTasks) -> None:
    """TODO: verify ownership, status == failed, retry_count == 0, then re-run processing."""
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Not built yet.")
