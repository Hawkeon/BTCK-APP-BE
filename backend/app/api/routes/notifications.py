import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Message,
    NotificationPublic,
    NotificationsPublic,
    Notification
)

router = APIRouter()

@router.get("/", response_model=NotificationsPublic)
def read_notifications(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve notifications for current user.
    """
    notifications = crud.get_notifications(
        session=session, recipient_id=current_user.id, skip=skip, limit=limit
    )
    count_statement = select(func.count()).select_from(Notification).where(Notification.recipient_id == current_user.id)
    count = session.exec(count_statement).one()
    return NotificationsPublic(data=notifications, count=count)

@router.get("/unread-count")
def get_unread_count(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Get unread notifications count.
    """
    statement = select(func.count()).select_from(Notification).where(
        Notification.recipient_id == current_user.id,
        Notification.is_read == False
    )
    count = session.exec(statement).one()
    return {"count": count}

@router.patch("/{notification_id}/read", response_model=NotificationPublic)
def mark_notification_read(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    notification_id: uuid.UUID,
) -> Any:
    """
    Mark a notification as read.
    """
    notification = crud.get_notification(
        session=session, notification_id=notification_id, recipient_id=current_user.id
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return crud.mark_notification_as_read(session=session, db_obj=notification)

@router.post("/mark-all-read", response_model=Message)
def mark_all_read(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Mark all notifications as read.
    """
    count = crud.mark_all_notifications_as_read(session=session, recipient_id=current_user.id)
    return Message(message=f"Marked {count} notifications as read")
