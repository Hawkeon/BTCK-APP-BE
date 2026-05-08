import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app import crud
from app.models import Budget, BudgetCreate, BudgetPublic, BudgetUpdate, BudgetsPublic, Message

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("/", response_model=BudgetsPublic)
def read_budgets(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve budgets for current user with spending summary.
    """
    budgets = crud.get_budgets(session=session, owner_id=current_user.id, skip=skip, limit=limit)
    budgets_public = []
    for budget in budgets:
        spent = crud.get_budget_spending(session=session, budget_id=budget.id, owner_id=current_user.id)
        budget_data = BudgetPublic.model_validate(budget)
        budget_data.spent = spent
        budgets_public.append(budget_data)
    return BudgetsPublic(data=budgets_public, count=len(budgets_public))


@router.post("/", response_model=BudgetPublic)
def create_budget(
    *, session: SessionDep, current_user: CurrentUser, budget_in: BudgetCreate
) -> Any:
    """
    Create new budget.
    """
    budget = crud.create_budget(
        session=session, budget_in=budget_in, owner_id=current_user.id
    )
    budget_public = BudgetPublic.model_validate(budget)
    budget_public.spent = 0.0
    return budget_public


@router.get("/{id}", response_model=BudgetPublic)
def read_budget(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get budget by ID with spending summary.
    """
    budget = crud.get_budget(session=session, budget_id=id, owner_id=current_user.id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    spent = crud.get_budget_spending(session=session, budget_id=id, owner_id=current_user.id)
    budget_public = BudgetPublic.model_validate(budget)
    budget_public.spent = spent
    return budget_public


@router.put("/{id}", response_model=BudgetPublic)
def update_budget(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    budget_in: BudgetUpdate,
) -> Any:
    """
    Update a budget.
    """
    db_budget = crud.get_budget(session=session, budget_id=id, owner_id=current_user.id)
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    updated = crud.update_budget(session=session, db_obj=db_budget, obj_in=budget_in)
    spent = crud.get_budget_spending(session=session, budget_id=id, owner_id=current_user.id)
    budget_public = BudgetPublic.model_validate(updated)
    budget_public.spent = spent
    return budget_public


@router.delete("/{id}")
def delete_budget(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a budget.
    """
    db_budget = crud.get_budget(session=session, budget_id=id, owner_id=current_user.id)
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    crud.delete_budget(session=session, db_obj=db_budget)
    return Message(message="Budget deleted successfully")