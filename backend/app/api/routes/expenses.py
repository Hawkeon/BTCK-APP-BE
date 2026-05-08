import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app import crud
from app.models import Expense, ExpenseCreate, ExpensePublic, ExpenseUpdate, ExpensesPublic, Message

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("/", response_model=ExpensesPublic)
def read_expenses(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    category_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Any:
    """
    Retrieve expenses with optional filters.
    """
    expenses = crud.get_expenses(
        session=session,
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
    )
    count = len(expenses)
    return ExpensesPublic(data=expenses, count=count)


@router.post("/", response_model=ExpensePublic)
def create_expense(
    *, session: SessionDep, current_user: CurrentUser, expense_in: ExpenseCreate
) -> Any:
    """
    Create new expense.
    """
    expense = crud.create_expense(
        session=session, expense_in=expense_in, owner_id=current_user.id
    )
    return expense


@router.get("/{id}", response_model=ExpensePublic)
def read_expense(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get expense by ID.
    """
    expense = crud.get_expense(session=session, expense_id=id, owner_id=current_user.id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.put("/{id}", response_model=ExpensePublic)
def update_expense(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    expense_in: ExpenseUpdate,
) -> Any:
    """
    Update an expense.
    """
    db_expense = crud.get_expense(session=session, expense_id=id, owner_id=current_user.id)
    if not db_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    updated = crud.update_expense(session=session, db_obj=db_expense, obj_in=expense_in)
    return updated


@router.delete("/{id}")
def delete_expense(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an expense.
    """
    db_expense = crud.get_expense(session=session, expense_id=id, owner_id=current_user.id)
    if not db_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    crud.delete_expense(session=session, db_obj=db_expense)
    return Message(message="Expense deleted successfully")