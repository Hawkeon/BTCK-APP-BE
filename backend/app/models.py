import uuid
from datetime import date, datetime, timezone

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore[assignment]
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    categories: list["Category"] = Relationship(back_populates="owner", cascade_delete=True)
    budgets: list["Budget"] = Relationship(back_populates="owner", cascade_delete=True)
    expenses: list["Expense"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore[assignment]


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# ============ Category Models ============

class CategoryBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=7)  # hex color


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=7)


class Category(CategoryBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="categories")
    budgets: list["Budget"] = Relationship(back_populates="category", cascade_delete=True)
    expenses: list["Expense"] = Relationship(back_populates="category", cascade_delete=True)


class CategoryPublic(CategoryBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ============ Budget Models ============

class BudgetBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    period: str = Field(max_length=20)  # monthly, weekly, yearly
    start_date: date = Field(default_factory=date.today)


class BudgetCreate(BudgetBase):
    category_id: uuid.UUID


class BudgetUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    amount: float | None = Field(default=None, gt=0)
    period: str | None = Field(default=None, max_length=20)
    start_date: date | None = None
    category_id: uuid.UUID | None = None


class Budget(BudgetBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="budgets")
    category_id: uuid.UUID = Field(
        foreign_key="category.id", nullable=False, ondelete="CASCADE"
    )
    category: Category | None = Relationship(back_populates="budgets")


class BudgetPublic(BudgetBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    category_id: uuid.UUID
    created_at: datetime | None = None
    spent: float = 0  # calculated field, not in DB


class BudgetsPublic(SQLModel):
    data: list[BudgetPublic]
    count: int


# ============ Expense Models ============

class ExpenseBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    expense_date: date = Field(default_factory=date.today, validation_alias="date")
    notes: str | None = Field(default=None, max_length=500)


class ExpenseCreate(ExpenseBase):
    category_id: uuid.UUID


class ExpenseUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    amount: float | None = Field(default=None, gt=0)
    expense_date: date | None = Field(default=None, validation_alias="date")
    notes: str | None = Field(default=None, max_length=500)
    category_id: uuid.UUID | None = None


class Expense(ExpenseBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="expenses")
    category_id: uuid.UUID = Field(
        foreign_key="category.id", nullable=False, ondelete="CASCADE"
    )
    category: Category | None = Relationship(back_populates="expenses")


class ExpensePublic(ExpenseBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    category_id: uuid.UUID
    created_at: datetime | None = None


class ExpensesPublic(SQLModel):
    data: list[ExpensePublic]
    count: int
