"""Auth: login, logout, current-session inspection, user management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlmodel import select

from app.config import settings
from app.deps import (
    SESSION_HEADER,
    CurrentUser,
    OwnerUser,
    RequestId,
    SessionDep,
    get_current_user_optional,
)
from app.models._base import AuditAction, Role, utcnow
from app.models.settings import AppSettings
from app.models.user import User
from app.schemas.auth import (
    FirstRunSetup,
    LoginRequest,
    LoginResponse,
    SessionStatus,
    UserCreate,
    UserPublic,
    UserUpdate,
)
from app.schemas.common import Message
from app.security import hash_password, needs_rehash, sign_session, verify_password
from app.services import audit
from app.services import sessions as session_svc

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/session", response_model=SessionStatus)
def get_session_status(
    db: SessionDep,
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> SessionStatus:
    s = db.get(AppSettings, 1)
    has_user = db.exec(select(User).limit(1)).first() is not None
    return SessionStatus(
        authenticated=user is not None,
        needs_setup=not has_user,
        user=UserPublic.model_validate(user, from_attributes=True) if user else None,
        ula_acknowledged=bool(s and s.ula_acknowledged_version),
        ula_version=s.ula_acknowledged_version if s else None,
    )


@router.post("/setup", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def first_run_setup(
    payload: FirstRunSetup,
    request: Request,
    response: Response,
    db: SessionDep,
    request_id: RequestId,
) -> LoginResponse:
    """Create the first account on a fresh install and sign it in.

    Only usable while no accounts exist; once one does, this is closed (409).
    """
    from app.services.seed import create_first_owner, seed_demo_scenarios

    if db.exec(select(User).limit(1)).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Setup has already been completed")

    user = create_first_owner(db, username=payload.username, password=payload.password)
    if settings.seed_demo_scenarios:
        seed_demo_scenarios(db, user)

    token = sign_session(user.id)
    session_svc.issue(
        db,
        user_id=user.id,
        token=token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    user.last_login_at = utcnow()
    db.flush()
    audit.record(
        db,
        actor=user,
        action=AuditAction.CREATE,
        entity_type="user",
        entity_id=user.id,
        summary=f"First-run account created: {user.email}",
        request_id=request_id,
    )
    audit.record(
        db,
        actor=user,
        action=AuditAction.LOGIN,
        entity_type="user",
        entity_id=user.id,
        summary=f"Logged in as {user.email}",
        request_id=request_id,
    )
    db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=False,  # local-only; HTTPS not assumed
    )
    return LoginResponse(
        user=UserPublic.model_validate(user, from_attributes=True),
        session_token=token,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: SessionDep,
    request_id: RequestId,
) -> LoginResponse:
    user = db.exec(select(User).where(User.email == payload.email.lower())).first()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    # Upgrade the stored hash if the Argon2 cost parameters have changed (M4).
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    # Opportunistically clear out stale rows so the table doesn't grow forever.
    session_svc.purge_expired(db)

    token = sign_session(user.id)
    session_svc.issue(
        db,
        user_id=user.id,
        token=token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    user.last_login_at = utcnow()
    db.flush()
    audit.record(
        db,
        actor=user,
        action=AuditAction.LOGIN,
        entity_type="user",
        entity_id=user.id,
        summary=f"Logged in as {user.email}",
        request_id=request_id,
    )
    db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=False,  # local-only; HTTPS not assumed
    )
    return LoginResponse(
        user=UserPublic.model_validate(user, from_attributes=True),
        session_token=token,
    )


@router.post("/logout", response_model=Message)
def logout(
    response: Response,
    db: SessionDep,
    user: CurrentUser,
    request_id: RequestId,
    session_token: Annotated[str | None, Cookie(alias=settings.session_cookie_name)] = None,
    header_token: Annotated[str | None, Header(alias=SESSION_HEADER)] = None,
) -> Message:
    # Revoke whichever token carried this request (cookie in the browser,
    # header in Tauri) so logout actually kills the session either way.
    token = session_token or header_token
    if token:
        session_svc.revoke(db, token)
    audit.record(
        db,
        actor=user,
        action=AuditAction.LOGOUT,
        entity_type="user",
        entity_id=user.id,
        summary=f"Logged out {user.email}",
        request_id=request_id,
    )
    db.commit()
    response.delete_cookie(settings.session_cookie_name)
    return Message(message="Signed out")


# ----------------------------------------------------------------- user mgmt


@router.get("/users", response_model=list[UserPublic])
def list_users(db: SessionDep, _: OwnerUser) -> list[UserPublic]:
    rows = db.exec(select(User).order_by(User.created_at.asc())).all()
    return [UserPublic.model_validate(u, from_attributes=True) for u in rows]


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate, db: SessionDep, owner: OwnerUser, request_id: RequestId
) -> UserPublic:
    if db.exec(select(User).where(User.email == payload.email.lower())).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=payload.email.lower(),
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    audit.record(
        db,
        actor=owner,
        action=AuditAction.CREATE,
        entity_type="user",
        entity_id=user.id,
        summary=f"Created user {user.email} ({user.role.value})",
        request_id=request_id,
    )
    db.commit()
    return UserPublic.model_validate(user, from_attributes=True)


@router.patch("/users/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: SessionDep,
    current: CurrentUser,
    request_id: RequestId,
) -> UserPublic:
    """Update a user.

    Owners can change anything on anyone. Everyone else may change only their
    OWN password and display name (the Settings "change your password" card),
    never role or active status.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    data = payload.model_dump(exclude_unset=True)

    is_self = current.id == user.id
    is_owner = Role.rank(current.role) >= Role.rank(Role.OWNER)
    if not is_owner:
        if not is_self:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Requires role >= owner")
        disallowed = set(data) - {"password", "display_name"}
        if disallowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "You may only change your own password or display name",
            )

    # Never let the last active owner be demoted or deactivated: with no owner
    # left, users and settings become unmanageable.
    demoting = data.get("role") is not None and data["role"] != Role.OWNER
    deactivating = data.get("is_active") is False
    if user.role == Role.OWNER and user.is_active and (demoting or deactivating):
        another_owner = db.exec(
            select(User)
            .where(User.role == Role.OWNER)
            .where(User.is_active == True)  # noqa: E712
            .where(User.id != user.id)
        ).first()
        if another_owner is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Cannot demote or deactivate the last active owner",
            )

    if "password" in data and data["password"] is not None:
        user.password_hash = hash_password(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    user.updated_at = utcnow()
    if deactivating:
        # Deactivation takes effect immediately, matching DELETE /users/{id}.
        session_svc.revoke_all_for_user(db, user.id)
    db.flush()
    audit.record(
        db,
        actor=current,
        action=AuditAction.UPDATE,
        entity_type="user",
        entity_id=user.id,
        summary=f"Updated user {user.email}",
        request_id=request_id,
    )
    db.commit()
    return UserPublic.model_validate(user, from_attributes=True)


@router.delete("/users/{user_id}", response_model=Message)
def deactivate_user(
    user_id: int, db: SessionDep, owner: OwnerUser, request_id: RequestId
) -> Message:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == owner.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate the current user")
    user.is_active = False
    user.updated_at = utcnow()
    # Kill any live sessions immediately so the deactivation takes effect now.
    session_svc.revoke_all_for_user(db, user.id)
    audit.record(
        db,
        actor=owner,
        action=AuditAction.UPDATE,
        entity_type="user",
        entity_id=user.id,
        summary=f"Deactivated user {user.email}",
        request_id=request_id,
    )
    db.commit()
    return Message(message="Deactivated")
