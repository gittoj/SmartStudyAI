import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.deps import CurrentParent, Db, OwnedChild
from app.core.security import CHILD_COOKIE, CHILD_MAX_AGE, hash_secret, sign_session, verify_secret
from app.models import Child, Worksheet
from app.services.storage_service import delete_file
from app.schemas import (
    ChildChoice, ChildProfile, CreateChildRequest, DeleteChildRequest, SelectChildRequest,
)

router = APIRouter(prefix="/api/children", tags=["children"])
MAX_CHILDREN = 4
MAX_PIN_FAILURES = 5
LOCK_MINUTES = 15


@router.get("", response_model=list[ChildProfile])
async def list_children(parent: CurrentParent, db: Db) -> list[Child]:
    return list((await db.execute(select(Child).where(Child.parent_id == parent.id))).scalars())


@router.post("", response_model=ChildProfile, status_code=status.HTTP_201_CREATED)
async def create_child_profile(body: CreateChildRequest, parent: CurrentParent, db: Db) -> Child:
    count = (await db.execute(select(func.count()).select_from(Child).where(Child.parent_id == parent.id))).scalar_one()
    if count >= MAX_CHILDREN:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can add up to four child profiles.")
    child = Child(parent_id=parent.id, username=body.username, level=body.level, pin_hash=hash_secret(body.pin))
    db.add(child)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is already used. Choose another one.")
    return child


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child_profile(body: DeleteChildRequest, child: OwnedChild, db: Db) -> None:
    if body.confirm_username.lower() != child.username:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Type the child's username to confirm.")
    keys = (await db.execute(select(Worksheet.storage_key).where(
        Worksheet.child_id == child.id, Worksheet.storage_key.is_not(None)))).scalars().all()
    for key in keys:
        await delete_file(key)
    await db.delete(child)  # attempts, progress, worksheets cascade
    await db.commit()


@router.get("/choices/list", response_model=list[ChildChoice])
async def list_child_choices(parent: CurrentParent, db: Db) -> list[Child]:
    """Practice screen: profiles this parent created."""
    return await list_children(parent, db)


@router.post("/{child_id}/select", response_model=ChildProfile)
async def select_child(body: SelectChildRequest, child: OwnedChild, db: Db, response: Response) -> Child:
    """Verify PIN server-side. Five failures lock the profile for 15 minutes."""
    now = datetime.now(timezone.utc)
    if child.locked_until and child.locked_until > now:
        raise HTTPException(status.HTTP_423_LOCKED, "Too many tries. Please try again later.")
    if not verify_secret(body.pin, child.pin_hash):
        child.failed_pin_attempts += 1
        if child.failed_pin_attempts >= MAX_PIN_FAILURES:
            child.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            child.failed_pin_attempts = 0
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That PIN is not right.")
    child.failed_pin_attempts = 0
    child.locked_until = None
    await db.commit()
    token = sign_session({"parentId": str(child.parent_id), "childId": str(child.id)}, CHILD_COOKIE)
    response.set_cookie(CHILD_COOKIE, token, max_age=CHILD_MAX_AGE, httponly=True,
                        secure=settings.cookie_secure, samesite="lax")
    return child


@router.post("/session/logout", status_code=status.HTTP_204_NO_CONTENT)
async def child_logout(response: Response) -> None:
    response.delete_cookie(CHILD_COOKIE)
