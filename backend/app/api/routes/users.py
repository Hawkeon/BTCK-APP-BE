import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlmodel import col, delete, func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
    limiter,
)
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import (
    AddMemberByEmailRequest,
    EventMember,
    EventMemberPublic,
    Message,
    UpdatePassword,
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import generate_new_account_email, send_email
from app.services.qr import generate_vietqr_url
from app.services.banks import bank_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", dependencies=[Depends(get_current_active_superuser)], response_model=UsersPublic)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """Retrieve users (admin only)."""
    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()
    statement = select(User).order_by(col(User.created_at).desc()).offset(skip).limit(limit)
    users = session.exec(statement).all()
    users_public = [UserPublic.model_validate(user) for user in users]
    return UsersPublic(data=users_public, count=count)


@router.post("/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """Create new user (admin only)."""
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system")
    user = crud.create_user(session=session, user_create=user_in)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(email_to=user_in.email, subject=email_data.subject, html_content=email_data.html_content)
    return user


@router.patch("/me", response_model=UserPublic)
async def update_user_me(*, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser) -> Any:
    """Update own user."""
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=409, detail="User with this email already exists")
    if user_in.bank_name:
        if not await bank_service.is_valid_bank(user_in.bank_name):
            raise HTTPException(status_code=400, detail=f"Mã ngân hàng không hợp lệ: {user_in.bank_name}")
            
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(*, session: SessionDep, body: UpdatePassword, current_user: CurrentUser) -> Any:
    """Update own password."""
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail="New password cannot be the same as the current one")
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """Get current user."""
    return current_user


@router.post("/me/avatar", response_model=UserPublic)
@limiter.limit("3/minute")
async def upload_avatar(
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> Any:
    """Upload avatar image for user profile."""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: JPEG, PNG, GIF, WebP")

    # Read file content
    content = await file.read()

    # Upload to storage (S3 or local)
    from app.services.storage import storage_service
    avatar_url = await storage_service.upload_image(content, file.filename or "avatar.png", "avatars")

    # Update user avatar_url
    current_user.avatar_url = avatar_url
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """Delete own user."""
    if current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Super users are not allowed to delete themselves")
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.get("/{user_id}/payment-qr", response_model=str)
def get_user_payment_qr(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    amount: int = 0,
    description: str | None = None,
) -> Any:
    """Get a dynamically generated VietQR URL for a user."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.bank_name or not user.account_number:
        raise HTTPException(
            status_code=400, 
            detail="User has not set up bank account information"
        )
        
    qr_url = generate_vietqr_url(
        bank_id=user.bank_name,
        account_no=user.account_number,
        amount=amount,
        account_name=user.account_holder or user.full_name,
        description=description or f"Thanh toan chia tien {settings.PROJECT_NAME}"
    )
    return qr_url


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """Register new user without login."""
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system")
    user_create = UserCreate.model_validate(user_in)
    user = crud.create_user(session=session, user_create=user_create)
    return user


@router.get("/search", response_model=list[UserPublic])
def search_users(
    session: SessionDep,
    current_user: CurrentUser,
    email: str,
) -> Any:
    """Search users by email (for inviting to events)."""
    users = crud.search_users_by_email(session=session, email=email, current_user_id=current_user.id)
    return [UserPublic.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> Any:
    """Get a specific user by id."""
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic)
def update_user(*, session: SessionDep, user_id: uuid.UUID, user_in: UserUpdate) -> Any:
    """Update a user (admin only)."""
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="The user with this id does not exist in the system")
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=409, detail="User with this email already exists")
    db_user = crud.update_user(session=session, db_user=db_user, user_in=user_in)
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID) -> Message:
    """Delete a user (admin only)."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(status_code=403, detail="Super users are not allowed to delete themselves")
    statement = delete(EventMember).where(EventMember.user_id == user_id)
    session.exec(statement)
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")