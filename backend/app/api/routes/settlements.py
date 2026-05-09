import uuid

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Message,
    Settlement,
    SettlementCreate,
    SettlementPublic,
    SettlementsPublic,
    User,
)

router = APIRouter(prefix="/events/{event_id}/settlements", tags=["settlements"])


def settlement_to_public(settlement: Settlement, session) -> SettlementPublic:
    from_user = session.get(User, settlement.from_user_id)
    to_user = session.get(User, settlement.to_user_id)
    return SettlementPublic(
        id=settlement.id,
        event_id=settlement.event_id,
        from_user_id=settlement.from_user_id,
        to_user_id=settlement.to_user_id,
        amount=settlement.amount,
        note=settlement.note,
        settled_at=settlement.settled_at,
        from_user_email=from_user.email if from_user else None,
        from_user_full_name=from_user.full_name if from_user else None,
        to_user_email=to_user.email if to_user else None,
        to_user_full_name=to_user.full_name if to_user else None,
    )


def check_event_access(event_id: uuid.UUID, session, current_user: CurrentUser) -> None:
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")


@router.get("/", response_model=SettlementsPublic)
def list_settlements(
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> SettlementsPublic:
    check_event_access(event_id, session, current_user)
    settlements = crud.get_settlements(session=session, event_id=event_id, skip=skip, limit=limit)
    settlement_list = [settlement_to_public(s, session) for s in settlements]
    return SettlementsPublic(data=settlement_list, count=len(settlement_list))


@router.post("/", response_model=SettlementPublic)
def create_settlement(
    event_id: uuid.UUID,
    settlement_in: SettlementCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> SettlementPublic:
    check_event_access(event_id, session, current_user)

    # Cannot settle with yourself
    if settlement_in.to_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot settle with yourself")

    # Verify target user is event member
    member_ids = crud.get_event_member_ids(session=session, event_id=event_id)
    if settlement_in.to_user_id not in member_ids:
        raise HTTPException(status_code=400, detail="Recipient must be an event member")

    settlement = crud.create_settlement(
        session=session,
        settlement_in=settlement_in,
        event_id=event_id,
        from_user_id=current_user.id,
    )
    return settlement_to_public(settlement, session)


@router.get("/{settlement_id}", response_model=SettlementPublic)
def get_settlement(
    event_id: uuid.UUID,
    settlement_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> SettlementPublic:
    check_event_access(event_id, session, current_user)
    settlement = crud.get_settlement(session=session, settlement_id=settlement_id, event_id=event_id)
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return settlement_to_public(settlement, session)


@router.delete("/{settlement_id}", response_model=Message)
def delete_settlement(
    event_id: uuid.UUID,
    settlement_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Message:
    check_event_access(event_id, session, current_user)
    settlement = crud.get_settlement(session=session, settlement_id=settlement_id, event_id=event_id)
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    # Only the person who made the settlement can delete it
    if settlement.from_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can delete this settlement")
    crud.delete_settlement(session=session, db_obj=settlement)
    return Message(message="Settlement deleted successfully")


@router.get("/my/balances", response_model=crud.EventBalances)
def get_my_event_balance(
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> crud.EventBalances:
    """Get current user's balance in event, factoring in settlements."""
    check_event_access(event_id, session, current_user)
    return crud.calculate_event_balances_with_settlements(session=session, event_id=event_id)