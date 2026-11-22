from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.deps import CurrentParent, Db
from app.core.security import (
    CHILD_COOKIE, PARENT_COOKIE, PARENT_MAX_AGE, clear_cookie, hash_secret, sign_session, verify_secret,
)
from app.models import Parent
from app.schemas import LoginRequest, ParentAccount, RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=ParentAccount, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: Db) -> Parent:
    parent = Parent(email=body.email.lower(), display_name=body.display_name, password_hash=hash_secret(body.password))
    db.add(parent)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    return parent


@router.post("/login", response_model=ParentAccount)
async def login(body: LoginRequest, db: Db, response: Response) -> Parent:
    parent = (await db.execute(select(Parent).where(Parent.email == body.email.lower()))).scalar_one_or_none()
    if parent is None or not verify_secret(body.password, parent.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is not right.")
    clear_cookie(response, CHILD_COOKIE)  # a grown-up is back: any child session on this device ends
    token = sign_session({"parentId": str(parent.id)}, PARENT_COOKIE)
    response.set_cookie(PARENT_COOKIE, token, max_age=PARENT_MAX_AGE, httponly=True,
                        secure=settings.cookie_secure, samesite="lax")
    return parent


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """Clears the parent session and any selected child profile."""
    clear_cookie(response, PARENT_COOKIE)
    clear_cookie(response, CHILD_COOKIE)


@router.get("/me", response_model=ParentAccount)
async def me(parent: CurrentParent) -> Parent:
    return parent
