from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.deps import CurrentParent, Db
from app.core.security import (
    CHILD_COOKIE, DUMMY_HASH, PARENT_COOKIE, PARENT_MAX_AGE, clear_cookie, hash_secret, sign_session, verify_secret,
)
from app.models import Parent
from app.schemas import LoginRequest, ParentAccount, RegisterRequest
from app.services import rate_limit_service as limits

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=ParentAccount, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, db: Db) -> Parent:
    ip = limits.client_ip(request)
    await limits.ensure_allowed(db, "register_ip", ip, settings.register_limit_ip, timedelta(hours=1))
    await limits.record(db, "register_ip", ip)
    parent = Parent(email=body.email.lower(), display_name=body.display_name, password_hash=hash_secret(body.password))
    db.add(parent)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    return parent


@router.post("/login", response_model=ParentAccount)
async def login(body: LoginRequest, request: Request, db: Db, response: Response) -> Parent:
    email, ip = body.email.lower(), limits.client_ip(request)
    window = timedelta(minutes=settings.login_window_minutes)
    # Checked before the password, so a blocked caller learns nothing about whether it was right.
    await limits.ensure_allowed(db, "login_email", email, settings.login_fail_limit_email, window)
    await limits.ensure_allowed(db, "login_ip", ip, settings.login_fail_limit_ip, window)
    parent = (await db.execute(select(Parent).where(Parent.email == email))).scalar_one_or_none()
    password_ok = verify_secret(body.password, parent.password_hash if parent else DUMMY_HASH)
    if parent is None or not password_ok:
        # Unknown emails count too, so the block cannot be used to discover which emails have accounts.
        await limits.record(db, "login_email", email)
        await limits.record(db, "login_ip", ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is not right.")
    await limits.clear(db, "login_email", email)
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
