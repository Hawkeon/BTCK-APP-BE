import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app import crud
from app.models import Category, CategoryCreate, CategoryPublic, CategoryUpdate, Message

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryPublic])
def read_categories(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve categories for current user.
    """
    categories = crud.get_categories(session=session, owner_id=current_user.id, skip=skip, limit=limit)
    return categories


@router.post("/", response_model=CategoryPublic)
def create_category(
    *, session: SessionDep, current_user: CurrentUser, category_in: CategoryCreate
) -> Any:
    """
    Create new category.
    """
    category = crud.create_category(
        session=session, category_in=category_in, owner_id=current_user.id
    )
    return category


@router.get("/{id}", response_model=CategoryPublic)
def read_category(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get category by ID.
    """
    category = crud.get_category(session=session, category_id=id, owner_id=current_user.id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{id}", response_model=CategoryPublic)
def update_category(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    category_in: CategoryUpdate,
) -> Any:
    """
    Update a category.
    """
    db_category = crud.get_category(session=session, category_id=id, owner_id=current_user.id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    updated = crud.update_category(session=session, db_obj=db_category, obj_in=category_in)
    return updated


@router.delete("/{id}")
def delete_category(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a category.
    """
    db_category = crud.get_category(session=session, category_id=id, owner_id=current_user.id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    crud.delete_category(session=session, db_obj=db_category)
    return Message(message="Category deleted successfully")