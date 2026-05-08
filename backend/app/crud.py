import uuid
from datetime import date
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    Budget, BudgetCreate, BudgetUpdate,
    Category, CategoryCreate, CategoryUpdate,
    Expense, ExpenseCreate, ExpenseUpdate,
    Item, ItemCreate, User, UserCreate, UserUpdate,
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


# Dummy hash to use for timing attack prevention when user is not found
# This is an Argon2 hash of a random password, used to ensure constant-time comparison
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        # Prevent timing attacks by running password verification even when user doesn't exist
        # This ensures the response time is similar whether or not the email exists
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# ============ Category CRUD ============

def create_category(*, session: Session, category_in: "CategoryCreate", owner_id: uuid.UUID) -> "Category":
    db_obj = Category.model_validate(category_in, update={"owner_id": owner_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_categories(*, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list["Category"]:
    statement = select(Category).where(Category.owner_id == owner_id).offset(skip).limit(limit)
    return session.exec(statement).all()


def get_category(*, session: Session, category_id: uuid.UUID, owner_id: uuid.UUID) -> "Category | None":
    statement = select(Category).where(Category.id == category_id, Category.owner_id == owner_id)
    return session.exec(statement).first()


def update_category(*, session: Session, db_obj: "Category", obj_in: "CategoryUpdate") -> "Category":
    data = obj_in.model_dump(exclude_unset=True)
    db_obj.sqlmodel_update(data)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def delete_category(*, session: Session, db_obj: "Category") -> None:
    session.delete(db_obj)
    session.commit()


# ============ Budget CRUD ============

def create_budget(*, session: Session, budget_in: "BudgetCreate", owner_id: uuid.UUID) -> "Budget":
    db_obj = Budget.model_validate(budget_in, update={"owner_id": owner_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_budgets(*, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list["Budget"]:
    statement = select(Budget).where(Budget.owner_id == owner_id).offset(skip).limit(limit)
    return session.exec(statement).all()


def get_budget(*, session: Session, budget_id: uuid.UUID, owner_id: uuid.UUID) -> "Budget | None":
    statement = select(Budget).where(Budget.id == budget_id, Budget.owner_id == owner_id)
    return session.exec(statement).first()


def update_budget(*, session: Session, db_obj: "Budget", obj_in: "BudgetUpdate") -> "Budget":
    data = obj_in.model_dump(exclude_unset=True)
    db_obj.sqlmodel_update(data)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def delete_budget(*, session: Session, db_obj: "Budget") -> None:
    session.delete(db_obj)
    session.commit()


def get_budget_spending(*, session: Session, budget_id: uuid.UUID, owner_id: uuid.UUID) -> float:
    budget = get_budget(session=session, budget_id=budget_id, owner_id=owner_id)
    if not budget:
        return 0.0
    from app.models import Expense
    period_start = budget.start_date
    statement = select(Expense).where(
        Expense.category_id == budget.category_id,
        Expense.owner_id == owner_id,
        Expense.date >= period_start
    )
    expenses = session.exec(statement).all()
    return sum(exp.amount for exp in expenses)


# ============ Expense CRUD ============

def create_expense(*, session: Session, expense_in: "ExpenseCreate", owner_id: uuid.UUID) -> "Expense":
    db_obj = Expense.model_validate(expense_in, update={"owner_id": owner_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_expenses(*, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100,
                 category_id: uuid.UUID | None = None, date_from: date | None = None, date_to: date | None = None) -> list["Expense"]:
    statement = select(Expense).where(Expense.owner_id == owner_id)
    if category_id:
        statement = statement.where(Expense.category_id == category_id)
    if date_from:
        statement = statement.where(Expense.date >= date_from)
    if date_to:
        statement = statement.where(Expense.date <= date_to)
    statement = statement.offset(skip).limit(limit).order_by(Expense.date.desc())
    return session.exec(statement).all()


def get_expense(*, session: Session, expense_id: uuid.UUID, owner_id: uuid.UUID) -> "Expense | None":
    statement = select(Expense).where(Expense.id == expense_id, Expense.owner_id == owner_id)
    return session.exec(statement).first()


def update_expense(*, session: Session, db_obj: "Expense", obj_in: "ExpenseUpdate") -> "Expense":
    data = obj_in.model_dump(exclude_unset=True)
    db_obj.sqlmodel_update(data)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def delete_expense(*, session: Session, db_obj: "Expense") -> None:
    session.delete(db_obj)
    session.commit()
