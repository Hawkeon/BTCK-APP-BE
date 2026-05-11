import uuid

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    AddMemberRequest,
    Event,
    EventBalances,
    EventCreate,
    EventMemberPublic,
    EventPublic,
    EventsPublic,
    Message,
    MyBalanceDetail,
    User,
)

router = APIRouter(prefix="/events", tags=["events"])


def event_to_public(event, session) -> EventPublic:
    members = crud.get_event_members(session=session, event_id=event.id)
    expenses = crud.get_expenses(session=session, event_id=event.id)
    return EventPublic(
        id=event.id,
        name=event.name,
        description=event.description,
        owner_id=event.owner_id,
        created_at=event.created_at,
        member_count=len(members),
        expense_count=len(expenses)
    )


@router.get("/", response_model=EventsPublic)
def list_events(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> EventsPublic:
    events = crud.get_events(session=session, user_id=current_user.id, skip=skip, limit=limit)
    event_list = [event_to_public(e, session) for e in events]
    return EventsPublic(data=event_list, count=len(event_list))


@router.post("/", response_model=EventPublic)
def create_event(
    event_in: EventCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventPublic:
    event = crud.create_event(session=session, event_in=event_in, owner_id=current_user.id)
    return event_to_public(event, session)


@router.get("/me/balance", response_model=MyBalanceDetail)
def get_my_balance(
    session: SessionDep,
    current_user: CurrentUser,
) -> MyBalanceDetail:
    """Get current user's balance across all events"""
    return crud.calculate_my_balance_summary(session=session, user_id=current_user.id)


@router.get("/{event_id}", response_model=EventPublic)
def get_event(
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventPublic:
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event_to_public(event, session)


@router.put("/{event_id}", response_model=EventPublic)
def update_event(
    event_id: uuid.UUID,
    event_in: EventCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventPublic:
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can update event")
    event = crud.update_event(session=session, db_obj=event, obj_in=event_in)
    return event_to_public(event, session)


@router.delete("/{event_id}", response_model=Message)
def delete_event(
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Message:
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can delete event")
    crud.delete_event(session=session, db_obj=event)
    return Message(message="Event deleted successfully")


@router.post("/{event_id}/members", response_model=EventMemberPublic)
def add_member(
    event_id: uuid.UUID,
    member_in: AddMemberRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventMemberPublic:
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    user = session.get(User, member_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    member = crud.add_member(session=session, event_id=event_id, user_id=member_in.user_id)
    return EventMemberPublic(
        id=member.id,
        user_id=member.user_id,
        joined_at=member.joined_at,
        user_email=user.email,
        user_full_name=user.full_name
    )


@router.delete("/{event_id}/members/{user_id}", response_model=Message)
def remove_member(
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Message:
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can remove members")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    success = crud.remove_member(session=session, event_id=event_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return Message(message="Member removed successfully")


@router.get("/{event_id}/balances", response_model=EventBalances)
def get_event_balances(
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventBalances:
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return crud.calculate_event_balances(session=session, event_id=event_id)