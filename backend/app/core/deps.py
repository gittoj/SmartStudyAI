import uuid
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    CHILD_COOKIE, CHILD_MAX_AGE, PARENT_COOKIE, PARENT_MAX_AGE, read_session,
)
from app.models import Child, Parent

Db = Annotated[AsyncSession, Depends(get_db)]


async def get_current_parent(
    db: Db, parent_session: Annotated[str | None, Cookie()] = None
) -> Parent:
    data = read_session(parent_session or "", PARENT_COOKIE, PARENT_MAX_AGE)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in.")
    parent = await db.get(Parent, uuid.UUID(data["parentId"]))
    if parent is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in.")
    return parent


CurrentParent = Annotated[Parent, Depends(get_current_parent)]


async def get_owned_child(child_id: uuid.UUID, db: Db, parent: CurrentParent) -> Child:
    """Return the child only if it belongs to the logged-in parent."""
    child = await db.get(Child, child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That child profile could not be found.")
    return child


async def get_current_child(
    db: Db, child_session: Annotated[str | None, Cookie()] = None
) -> Child:
    """Child session is separate from the parent session; tied to one parent + one child."""
    data = read_session(child_session or "", CHILD_COOKIE, CHILD_MAX_AGE)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Choose your profile first.")
    child = await db.get(Child, uuid.UUID(data["childId"]))
    if child is None or str(child.parent_id) != data["parentId"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Choose your profile first.")
    return child


OwnedChild = Annotated[Child, Depends(get_owned_child)]
CurrentChild = Annotated[Child, Depends(get_current_child)]
