import uuid

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    AddMemberByEmailRequest,
    EventBalances,
    EventCreate,
    EventMemberPublic,
    EventPublic,
    EventsPublic,
    EventStats,
    InviteCodeCreate,
    InviteCodePublic,
    Message,
    MyBalanceDetail,
    SimplifiedDebtsResponse,
    User,
)

router = APIRouter(prefix="/events", tags=["events"])


def event_to_public(event, _session: SessionDep) -> EventPublic:
    return EventPublic(
        id=event.id,
        name=event.name,
        description=event.description,
        created_by_id=event.created_by_id,
        created_at=event.created_at,
        member_count=len(event.members),
        expense_count=len(event.expenses)
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
    event = crud.create_event(session=session, event_in=event_in, created_by_id=current_user.id)
    return event_to_public(event, session)


@router.get("/me/balance", response_model=MyBalanceDetail)
def get_my_balance(session: SessionDep, current_user: CurrentUser) -> MyBalanceDetail:
    """Get current user's balance across all events."""
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
    if event.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only creator can update event")
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
    if event.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only creator can delete event")
    crud.delete_event(session=session, db_obj=event)
    return Message(message="Event deleted successfully")


@router.post("/{event_id}/members", response_model=EventMemberPublic)
def add_member_by_email(
    event_id: uuid.UUID,
    member_in: AddMemberByEmailRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventMemberPublic:
    """Add member to event by email."""
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Find user by email
    user = crud.get_user_by_email(session=session, email=member_in.email)
    if not user:
        raise HTTPException(status_code=404, detail="User with this email not found")

    # Add member
    member = crud.add_member_by_user_id(session=session, event_id=event_id, user_id=user.id)
    return EventMemberPublic(
        event_id=event_id,
        user_id=user.id,
        joined_at=member.joined_at,
        user_email=user.email,
        user_full_name=user.full_name,
        user_qr_code_url=user.qr_code_url,
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
    if event.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only creator can remove members")
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


@router.get("/{event_id}/balances/simplify", response_model=SimplifiedDebtsResponse)
def simplify_event_debts(
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> SimplifiedDebtsResponse:
    """Calculate simplified debts - minimum cash flow algorithm."""
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return crud.simplify_event_debts(session=session, event_id=event_id)


@router.post("/{event_id}/invite", response_model=InviteCodePublic)
def create_invite_code(
    event_id: uuid.UUID,
    invite_in: InviteCodeCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> InviteCodePublic:
    """Create an invite code for sharing the event."""
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    invite = crud.generate_invite_code(
        session=session,
        event_id=event_id,
        created_by_id=current_user.id,
        expires_in_hours=invite_in.expires_in_hours,
        max_uses=invite_in.max_uses,
    )

    return InviteCodePublic(
        code=invite.code,
        expires_at=invite.expires_at,
        invite_url=f"/join/{invite.code}",
        created_at=invite.created_at,
    )


@router.get("/{event_id}/stats", response_model=EventStats)
def get_event_stats(
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventStats:
    """Get event statistics."""
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return crud.get_event_stats(session=session, event_id=event_id, user_id=current_user.id)


@router.post("/join/{code}", response_model=EventMemberPublic)
def join_event_by_code(
    code: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventMemberPublic:
    """Join an event using an invite code."""
    if not crud.is_invite_code_valid(session=session, code=code):
        raise HTTPException(status_code=400, detail="Invalid or expired invite code")

    invite = crud.get_invite_code_by_code(session=session, code=code)
    if not invite or not invite.event_id:
        raise HTTPException(status_code=400, detail="Invalid invite code")

    event = crud.get_event(session=session, event_id=invite.event_id, user_id=current_user.id)
    if event:
        # User is already a member
        members = crud.get_event_members(session=session, event_id=invite.event_id)
        for m in members:
            if m.user_id == current_user.id:
                user = session.get(User, current_user.id)
                return EventMemberPublic(
                    event_id=invite.event_id,
                    user_id=current_user.id,
                    joined_at=m.joined_at,
                    user_email=user.email if user else None,
                    user_full_name=user.full_name if user else None,
                    user_qr_code_url=user.qr_code_url if user else None,
                )

    # Add user to event
    crud.use_invite_code(session=session, code=code)
    member = crud.add_member_by_user_id(session=session, event_id=invite.event_id, user_id=current_user.id)
    user = session.get(User, current_user.id)

    return EventMemberPublic(
        event_id=invite.event_id,
        user_id=current_user.id,
        joined_at=member.joined_at,
        user_email=user.email if user else None,
        user_full_name=user.full_name if user else None,
        user_qr_code_url=user.qr_code_url if user else None,
    )
