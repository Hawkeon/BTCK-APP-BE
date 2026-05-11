import uuid

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ExpenseCreate,
    ExpensePublic,
    ExpenseSplitPublic,
    ExpenseUpdate,
    ExpensesPublic,
    Message,
    User,
)

router = APIRouter(prefix="/events/{event_id}/expenses", tags=["expenses"])


def expense_to_public(expense, session) -> ExpensePublic:
    payer = session.get(User, expense.payer_id)
    splits = []
    for s in expense.splits:
        user = session.get(User, s.user_id)
        splits.append(ExpenseSplitPublic(
            id=s.id,
            user_id=s.user_id,
            amount_owed=s.amount_owed,
            is_excluded=s.is_excluded,
            user_email=user.email if user else None,
            user_full_name=user.full_name if user else None
        ))
    return ExpensePublic(
        id=expense.id,
        description=expense.description,
        amount=expense.amount,
        expense_date=expense.expense_date,
        category=expense.category,
        event_id=expense.event_id,
        payer_id=expense.payer_id,
        split_type=expense.split_type,
        created_at=expense.created_at,
        payer_email=payer.email if payer else None,
        payer_full_name=payer.full_name if payer else None,
        splits=splits
    )


def check_event_access(event_id: uuid.UUID, session, current_user: CurrentUser) -> None:
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")


@router.get("/", response_model=ExpensesPublic)
def list_expenses(
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> ExpensesPublic:
    check_event_access(event_id, session, current_user)
    expenses = crud.get_expenses(session=session, event_id=event_id, skip=skip, limit=limit)
    expense_list = [expense_to_public(e, session) for e in expenses]
    return ExpensesPublic(data=expense_list, count=len(expense_list))


@router.post("/", response_model=ExpensePublic)
def create_expense(
    event_id: uuid.UUID,
    expense_in: ExpenseCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ExpensePublic:
    check_event_access(event_id, session, current_user)

    # Validate split_type
    if expense_in.split_type not in ("equal", "custom"):
        raise HTTPException(status_code=400, detail="split_type must be 'equal' or 'custom'")

    # Validate custom splits
    if expense_in.split_type == "custom":
        if not expense_in.splits:
            raise HTTPException(status_code=400, detail="Custom split requires splits array")
        # Check that split amounts equal total
        total_splits = sum(s.amount for s in expense_in.splits)
        if abs(total_splits - expense_in.amount) > 0.01:
            raise HTTPException(status_code=400, detail="Split amounts must equal total amount")

    expense = crud.create_expense(
        session=session,
        expense_in=expense_in,
        event_id=event_id,
        payer_id=current_user.id
    )
    return expense_to_public(expense, session)


@router.get("/{expense_id}", response_model=ExpensePublic)
def get_expense(
    event_id: uuid.UUID,
    expense_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> ExpensePublic:
    check_event_access(event_id, session, current_user)
    expense = crud.get_expense(session=session, expense_id=expense_id, event_id=event_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense_to_public(expense, session)


@router.put("/{expense_id}", response_model=ExpensePublic)
def update_expense(
    event_id: uuid.UUID,
    expense_id: uuid.UUID,
    expense_in: ExpenseUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ExpensePublic:
    check_event_access(event_id, session, current_user)
    expense = crud.get_expense(session=session, expense_id=expense_id, event_id=event_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.payer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only payer can update expense")
    expense = crud.update_expense(session=session, db_obj=expense, obj_in=expense_in)
    return expense_to_public(expense, session)


@router.delete("/{expense_id}", response_model=Message)
def delete_expense(
    event_id: uuid.UUID,
    expense_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Message:
    check_event_access(event_id, session, current_user)
    expense = crud.get_expense(session=session, expense_id=expense_id, event_id=event_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.payer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only payer can delete expense")
    crud.delete_expense(session=session, db_obj=expense)
    return Message(message="Expense deleted successfully")