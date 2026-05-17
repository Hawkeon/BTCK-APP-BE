import uuid
from enum import Enum
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
    bank_name: str | None = Field(default=None, max_length=50)
    account_number: str | None = Field(default=None, max_length=50)
    account_holder: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=500, nullable=True)


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
    bank_name: str | None = Field(default=None, max_length=50)
    account_number: str | None = Field(default=None, max_length=50)
    account_holder: str | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    created_events: list["Event"] = Relationship(
        back_populates="creator",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "[Event.created_by_id]",
            "primaryjoin": "User.id == Event.created_by_id",
        },
    )
    memberships: list["EventMember"] = Relationship(
        back_populates="user",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "[EventMember.user_id]",
            "primaryjoin": "User.id == EventMember.user_id",
        },
    )
    expense_splits: list["ExpenseSplit"] = Relationship(
        back_populates="user",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "[ExpenseSplit.user_id]",
            "primaryjoin": "User.id == ExpenseSplit.user_id",
        },
    )


class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# FCM Tokens
class UserFCMToken(SQLModel, table=True):
    __tablename__ = "user_fcm_tokens"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    fcm_token: str = Field(index=True)
    device_type: str | None = Field(default=None, max_length=50)  # e.g., "android", "ios"
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class FCMTokenCreate(SQLModel):
    fcm_token: str
    device_type: str | None = None


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
    __tablename__ = "events"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    created_by_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )
    creator: Optional["User"] = Relationship(
        back_populates="created_events",
        sa_relationship_kwargs={
            "foreign_keys": "[Event.created_by_id]",
            "primaryjoin": "Event.created_by_id == User.id",
        },
    )
    members: list["EventMember"] = Relationship(
        back_populates="event",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "[EventMember.event_id]",
            "primaryjoin": "Event.id == EventMember.event_id",
        },
    )
    expenses: list["Expense"] = Relationship(
        back_populates="event",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "[Expense.event_id]",
            "primaryjoin": "Event.id == Expense.event_id",
        },
    )
    settlements: list["Settlement"] = Relationship(
        back_populates="event",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "[Settlement.event_id]",
            "primaryjoin": "Event.id == Settlement.event_id",
        },
    )


class EventPublic(EventBase):
    id: uuid.UUID
    created_by_id: uuid.UUID
    created_at: datetime | None = None
    member_count: int = 0
    expense_count: int = 0


class EventsPublic(SQLModel):
    data: list[EventPublic]
    count: int


# ============ Event Member Models ============

class EventMember(SQLModel, table=True):
    __tablename__ = "event_members"
    __table_args__ = ({"schema": "public"})  # Ensure composite PK works properly

    event_id: uuid.UUID = Field(
        foreign_key="events.id", nullable=False, ondelete="CASCADE", primary_key=True
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE", primary_key=True
    )
    joined_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    event: Optional["Event"] = Relationship(
        back_populates="members",
        sa_relationship_kwargs={
            "foreign_keys": "[EventMember.event_id]",
            "primaryjoin": "EventMember.event_id == Event.id",
        },
    )
    user: Optional["User"] = Relationship(
        back_populates="memberships",
        sa_relationship_kwargs={
            "foreign_keys": "[EventMember.user_id]",
            "primaryjoin": "EventMember.user_id == User.id",
        },
    )


class EventMemberPublic(SQLModel):
    event_id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime | None = None
    user_email: str | None = None
    user_full_name: str | None = None


class AddMemberByEmailRequest(SQLModel):
    email: EmailStr


# ============ Expense Models ============

class ExpenseBase(SQLModel):
    description: str = Field(min_length=1, max_length=255)
    amount: int = Field(gt=0)
    category: str | None = Field(default=None, max_length=50)
    image_url: str | None = Field(default=None, max_length=500, nullable=True)
    expense_date: date = Field(default_factory=date.today)


class ExpenseCreate(SQLModel):
    description: str = Field(min_length=1, max_length=255)
    amount: int = Field(gt=0)
    category: str | None = Field(default=None, max_length=50)
    expense_date: date | None = Field(default_factory=date.today)
    payer_id: uuid.UUID
    splits: list["ExpenseSplitCreate"] = Field(min_length=1)


class ExpenseSplitCreate(SQLModel):
    user_id: uuid.UUID
    amount_owed: int = Field(gt=0)


class ExpenseUpdate(SQLModel):
    description: str | None = Field(default=None, min_length=1, max_length=255)
    amount: int | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, max_length=50)
    expense_date: date | None = Field(default=None)


class Expense(ExpenseBase, table=True):
    __tablename__ = "expenses"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    created_by_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )
    event_id: uuid.UUID = Field(
        foreign_key="events.id", nullable=False, ondelete="CASCADE"
    )
    payer_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )
    event: Optional["Event"] = Relationship(
        back_populates="expenses",
        sa_relationship_kwargs={"foreign_keys": "[Expense.event_id]"},
    )
    creator: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Expense.created_by_id]",
            "primaryjoin": "Expense.created_by_id == User.id",
        },
    )
    payer: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Expense.payer_id]",
            "primaryjoin": "Expense.payer_id == User.id",
        },
    )
    splits: list["ExpenseSplit"] = Relationship(
        back_populates="expense",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "[ExpenseSplit.expense_id]",
            "primaryjoin": "Expense.id == ExpenseSplit.expense_id",
        },
    )


class ExpensePublic(ExpenseBase):
    id: uuid.UUID
    event_id: uuid.UUID
    created_by_id: uuid.UUID
    payer_id: uuid.UUID
    created_at: datetime | None = None
    payer_email: str | None = None
    payer_full_name: str | None = None
    splits: list["ExpenseSplitPublic"] = []


class ExpenseSplit(SQLModel, table=True):
    __tablename__ = "expense_splits"
    expense_id: uuid.UUID = Field(
        foreign_key="expenses.id", nullable=False, ondelete="CASCADE", primary_key=True
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE", primary_key=True
    )
    amount_owed: int = Field(gt=0)
    expense: Optional["Expense"] = Relationship(
        back_populates="splits",
        sa_relationship_kwargs={
            "foreign_keys": "[ExpenseSplit.expense_id]",
            "primaryjoin": "ExpenseSplit.expense_id == Expense.id",
        },
    )
    user: Optional["User"] = Relationship(
        back_populates="expense_splits",
        sa_relationship_kwargs={
            "foreign_keys": "[ExpenseSplit.user_id]",
            "primaryjoin": "ExpenseSplit.user_id == User.id",
        },
    )


class ExpenseSplitPublic(SQLModel):
    user_id: uuid.UUID
    amount_owed: int
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
    bank_name: str | None = None
    account_number: str | None = None
    account_holder: str | None = None
    total_paid: int
    total_owed: int
    net_balance: int  # positive = others owe user, negative = user owes


class EventBalances(SQLModel):
    event_id: uuid.UUID
    event_name: str
    balances: list[UserBalance]


class MyBalanceSummary(SQLModel):
    total_you_owe: int
    total_owed_to_you: int
    net_balance: int  # positive = you are owed, negative = you owe


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
    amount: int = Field(gt=0)


class SettlementCreate(SQLModel):
    from_user_id: uuid.UUID
    to_user_id: uuid.UUID
    amount: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)
    idempotency_key: uuid.UUID


class Settlement(SettlementBase, table=True):
    __tablename__ = "settlements"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_id: uuid.UUID = Field(
        foreign_key="events.id", nullable=False, ondelete="CASCADE"
    )
    from_user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )
    to_user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )
    amount: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)
    idempotency_key: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        unique=True,
        index=True,
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    event: Optional["Event"] = Relationship(
        back_populates="settlements",
        sa_relationship_kwargs={
            "foreign_keys": "[Settlement.event_id]",
            "primaryjoin": "Settlement.event_id == Event.id",
        },
    )
    from_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Settlement.from_user_id]",
            "primaryjoin": "Settlement.from_user_id == User.id",
        },
    )
    to_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Settlement.to_user_id]",
            "primaryjoin": "Settlement.to_user_id == User.id",
        },
    )


class SettlementPublic(SettlementBase):
    id: uuid.UUID
    event_id: uuid.UUID
    from_user_id: uuid.UUID
    to_user_id: uuid.UUID
    note: str | None = None
    idempotency_key: uuid.UUID
    created_at: datetime | None = None
    from_user_email: str | None = None
    from_user_full_name: str | None = None
    to_user_email: str | None = None
    to_user_full_name: str | None = None


class SettlementsPublic(SQLModel):
    data: list[SettlementPublic]
    count: int


# ============ Invite Models ============

class InviteCode(SQLModel, table=True):
    __tablename__ = "invite_codes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_id: uuid.UUID = Field(foreign_key="events.id", nullable=False, ondelete="CASCADE")
    code: str = Field(unique=True, index=True, max_length=20)
    created_by_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    expires_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    max_uses: int | None = Field(default=None)
    use_count: int = Field(default=0)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    event: Optional["Event"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[InviteCode.event_id]",
            "primaryjoin": "InviteCode.event_id == Event.id",
        },
    )
    creator: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[InviteCode.created_by_id]",
            "primaryjoin": "InviteCode.created_by_id == User.id",
        },
    )


class InviteCodeCreate(SQLModel):
    expires_in_hours: int | None = Field(default=None, ge=1, le=720)  # Max 30 days
    max_uses: int | None = Field(default=None, ge=1, le=100)


class InviteCodePublic(SQLModel):
    code: str
    expires_at: datetime | None = None
    invite_url: str
    created_at: datetime | None = None


# ============ Simplify Debts Models ============

class SimplifiedDebt(SQLModel):
    from_user_id: uuid.UUID
    from_user_email: str
    from_user_full_name: str | None
    to_user_id: uuid.UUID
    to_user_email: str
    to_user_full_name: str | None
    amount: int


class SimplifiedDebtsResponse(SQLModel):
    event_id: uuid.UUID
    debts: list[SimplifiedDebt]


# ============ Event Stats Models ============

class EventStats(SQLModel):
    event_id: uuid.UUID
    total_spent: int
    expense_count: int
    member_count: int
    your_total_paid: int
    your_total_owed: int
    your_net_balance: int


# ============ Notification Models ============

class NotificationType(str, Enum):
    EXPENSE_CREATED = "EXPENSE_CREATED"
    MEMBER_ADDED = "MEMBER_ADDED"
    SETTLEMENT_RECORDED = "SETTLEMENT_RECORDED"


class NotificationBase(SQLModel):
    title: str = Field(max_length=255)
    content: str
    type: NotificationType
    event_id: uuid.UUID | None = Field(default=None, foreign_key="events.id")
    reference_id: uuid.UUID | None = Field(default=None)


class Notification(NotificationBase, table=True):
    __tablename__ = "notifications"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    recipient_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    sender_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    is_read: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    recipient: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Notification.recipient_id]",
            "primaryjoin": "Notification.recipient_id == User.id",
        }
    )
    sender: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Notification.sender_id]",
            "primaryjoin": "Notification.sender_id == User.id",
        }
    )


class NotificationPublic(NotificationBase):
    id: uuid.UUID
    sender_id: uuid.UUID | None
    is_read: bool
    created_at: datetime


class NotificationsPublic(SQLModel):
    data: list[NotificationPublic]
    count: int