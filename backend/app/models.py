import uuid
from datetime import date, datetime, timezone
from typing import Optional

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# ============ User Models ============

class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    owned_events: list["Event"] = Relationship(back_populates="owner", cascade_delete=True)
    memberships: list["EventMember"] = Relationship(back_populates="user", cascade_delete=True)


class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# ============ Event Models ============

class EventBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class EventCreate(EventBase):
    pass


class EventUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class Event(EventBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: Optional["User"] = Relationship(back_populates="owned_events")
    members: list["EventMember"] = Relationship(back_populates="event", cascade_delete=True)
    expenses: list["Expense"] = Relationship(back_populates="event", cascade_delete=True)
    settlements: list["Settlement"] = Relationship(back_populates="event", cascade_delete=True)


class EventPublic(EventBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None
    member_count: int = 0
    expense_count: int = 0


class EventsPublic(SQLModel):
    data: list[EventPublic]
    count: int


# ============ Event Member Models ============

class EventMember(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_id: uuid.UUID = Field(
        foreign_key="event.id", nullable=False, ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    joined_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    event: Optional["Event"] = Relationship(back_populates="members")
    user: Optional["User"] = Relationship(back_populates="memberships")


class EventMemberPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime | None = None
    user_email: str | None = None
    user_full_name: str | None = None


class AddMemberRequest(SQLModel):
    user_id: uuid.UUID


# ============ Expense Models ============

class ExpenseBase(SQLModel):
    description: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    expense_date: date = Field(default_factory=date.today)
    category: str | None = Field(default=None, max_length=50)  # food, transport, rent, utilities, other


class ExpenseCreate(SQLModel):
    description: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    expense_date: date = Field(default_factory=date.today)
    category: str | None = Field(default=None, max_length=50)
    split_type: str = Field(default="equal", max_length=20)  # "equal" or "custom"
    # For equal split: which user_ids to include (all members if empty)
    include_user_ids: list[uuid.UUID] = []
    # For custom split: exact amounts per user
    splits: list["CustomSplit"] = []


class CustomSplit(SQLModel):
    user_id: uuid.UUID
    amount: float = Field(gt=0)


class ExpenseUpdate(SQLModel):
    description: str | None = Field(default=None, min_length=1, max_length=255)
    amount: float | None = Field(default=None, gt=0)
    expense_date: date | None = None
    category: str | None = Field(default=None, max_length=50)


class Expense(ExpenseBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    event_id: uuid.UUID = Field(
        foreign_key="event.id", nullable=False, ondelete="CASCADE"
    )
    payer_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    split_type: str = Field(default="equal", max_length=20)
    event: Optional["Event"] = Relationship(back_populates="expenses")
    payer: Optional["User"] = Relationship()
    splits: list["ExpenseSplit"] = Relationship(back_populates="expense", cascade_delete=True)


class ExpenseSplit(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    expense_id: uuid.UUID = Field(
        foreign_key="expense.id", nullable=False, ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    amount_owed: float = Field(gt=0)
    is_excluded: bool = Field(default=False)  # True = not part of this expense
    expense: Optional["Expense"] = Relationship(back_populates="splits")
    user: Optional["User"] = Relationship()


class ExpensePublic(ExpenseBase):
    id: uuid.UUID
    event_id: uuid.UUID
    payer_id: uuid.UUID
    split_type: str
    created_at: datetime | None = None
    payer_email: str | None = None
    payer_full_name: str | None = None
    splits: list["ExpenseSplitPublic"] = []


class ExpenseSplitPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount_owed: float
    is_excluded: bool
    user_email: str | None = None
    user_full_name: str | None = None


class ExpensesPublic(SQLModel):
    data: list[ExpensePublic]
    count: int


# ============ Balance Models ============

class UserBalance(SQLModel):
    user_id: uuid.UUID
    user_email: str
    user_full_name: str | None
    total_paid: float
    total_owed: float
    net_balance: float  # positive = others owe user, negative = user owes


class EventBalances(SQLModel):
    event_id: uuid.UUID
    event_name: str
    balances: list[UserBalance]


class MyBalanceSummary(SQLModel):
    total_you_owe: float
    total_owed_to_you: float
    net_balance: float  # positive = you are owed, negative = you owe


class MyBalanceDetail(SQLModel):
    events: list[EventBalances]
    summary: MyBalanceSummary


# ============ Generic Models ============

class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshTokenRequest(SQLModel):
    refresh_token: str


class TokenPayload(SQLModel):
    sub: str | None = None
    exp: int | None = None
    type: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# ============ Settlement Models ============

class SettlementBase(SQLModel):
    amount: float = Field(gt=0)


class SettlementCreate(SettlementBase):
    to_user_id: uuid.UUID  # who receives the payment
    note: str | None = Field(default=None, max_length=255)


class Settlement(SettlementBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_id: uuid.UUID = Field(
        foreign_key="event.id", nullable=False, ondelete="CASCADE"
    )
    from_user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    to_user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    amount: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)
    settled_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    event: Optional["Event"] = Relationship(back_populates="settlements")
    from_user: Optional["User"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Settlement.from_user_id]"})
    to_user: Optional["User"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Settlement.to_user_id]"})


class SettlementPublic(SettlementBase):
    id: uuid.UUID
    event_id: uuid.UUID
    from_user_id: uuid.UUID
    to_user_id: uuid.UUID
    note: str | None = None
    settled_at: datetime | None = None
    from_user_email: str | None = None
    from_user_full_name: str | None = None
    to_user_email: str | None = None
    to_user_full_name: str | None = None


class SettlementsPublic(SQLModel):
    data: list[SettlementPublic]
    count: int