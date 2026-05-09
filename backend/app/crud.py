import uuid
from datetime import date
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    AddMemberRequest,
    CustomSplit,
    Event,
    EventBalances,
    EventCreate,
    EventMember,
    EventMemberPublic,
    EventPublic,
    EventUpdate,
    Expense,
    ExpenseCreate,
    ExpensePublic,
    ExpenseSplit,
    ExpenseSplitPublic,
    ExpenseUpdate,
    MyBalanceDetail,
    MyBalanceSummary,
    User,
    UserBalance,
    UserCreate,
    UserUpdate,
)

# Dummy hash for timing attack prevention when user not found
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


# ============ User CRUD ============

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
    return session.exec(statement).first()


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
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


# ============ Event CRUD ============

def create_event(*, session: Session, event_in: EventCreate, owner_id: uuid.UUID) -> Event:
    db_obj = Event.model_validate(event_in, update={"owner_id": owner_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    # Auto-add owner as member
    member = EventMember(event_id=db_obj.id, user_id=owner_id)
    session.add(member)
    session.commit()
    return db_obj


def get_events(*, session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[Event]:
    statement = (
        select(Event)
        .join(EventMember, Event.id == EventMember.event_id)
        .where(EventMember.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return session.exec(statement).all()


def get_event(*, session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> Event | None:
    statement = (
        select(Event)
        .join(EventMember, Event.id == EventMember.event_id)
        .where(Event.id == event_id, EventMember.user_id == user_id)
    )
    return session.exec(statement).first()


def is_event_member(*, session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    statement = select(EventMember).where(
        EventMember.event_id == event_id, EventMember.user_id == user_id
    )
    return session.exec(statement).first() is not None


def is_event_owner(*, session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    statement = select(Event).where(
        Event.id == event_id, Event.owner_id == user_id
    )
    return session.exec(statement).first() is not None


def update_event(*, session: Session, db_obj: Event, obj_in: EventUpdate) -> Event:
    data = obj_in.model_dump(exclude_unset=True)
    db_obj.sqlmodel_update(data)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def delete_event(*, session: Session, db_obj: Event) -> None:
    session.delete(db_obj)
    session.commit()


# ============ Event Member CRUD ============

def add_member(*, session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> EventMember:
    existing = session.exec(
        select(EventMember).where(
            EventMember.event_id == event_id, EventMember.user_id == user_id
        )
    ).first()
    if existing:
        return existing
    db_obj = EventMember(event_id=event_id, user_id=user_id)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def remove_member(*, session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    member = session.exec(
        select(EventMember).where(
            EventMember.event_id == event_id, EventMember.user_id == user_id
        )
    ).first()
    if not member:
        return False
    session.delete(member)
    session.commit()
    return True


def get_event_members(*, session: Session, event_id: uuid.UUID) -> list[EventMember]:
    statement = select(EventMember).where(EventMember.event_id == event_id)
    return session.exec(statement).all()


def get_event_member_ids(*, session: Session, event_id: uuid.UUID) -> list[uuid.UUID]:
    members = get_event_members(session=session, event_id=event_id)
    return [m.user_id for m in members]


# ============ Expense CRUD ============

def create_expense(*, session: Session, expense_in: ExpenseCreate, event_id: uuid.UUID, payer_id: uuid.UUID) -> Expense:
    db_obj = Expense(
        description=expense_in.description,
        amount=expense_in.amount,
        expense_date=expense_in.expense_date,
        category=expense_in.category,
        event_id=event_id,
        payer_id=payer_id,
        split_type=expense_in.split_type,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)

    # Create splits based on split_type
    if expense_in.split_type == "equal":
        # Include all members or specific users if provided
        if expense_in.include_user_ids:
            user_ids = expense_in.include_user_ids
        else:
            user_ids = get_event_member_ids(session=session, event_id=event_id)

        split_amount = expense_in.amount / len(user_ids) if user_ids else 0
        for uid in user_ids:
            split = ExpenseSplit(
                expense_id=db_obj.id,
                user_id=uid,
                amount_owed=round(split_amount, 2),
                is_excluded=False,
            )
            session.add(split)
    else:
        # Custom splits
        for cs in expense_in.splits:
            split = ExpenseSplit(
                expense_id=db_obj.id,
                user_id=cs.user_id,
                amount_owed=cs.amount,
                is_excluded=False,
            )
            session.add(split)

    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_expenses(*, session: Session, event_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[Expense]:
    statement = (
        select(Expense)
        .where(Expense.event_id == event_id)
        .offset(skip)
        .limit(limit)
        .order_by(Expense.expense_date.desc())
    )
    return session.exec(statement).all()


def get_expense(*, session: Session, expense_id: uuid.UUID, event_id: uuid.UUID) -> Expense | None:
    statement = select(Expense).where(Expense.id == expense_id, Expense.event_id == event_id)
    return session.exec(statement).first()


def update_expense(*, session: Session, db_obj: Expense, obj_in: ExpenseUpdate) -> Expense:
    data = obj_in.model_dump(exclude_unset=True)
    db_obj.sqlmodel_update(data)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def delete_expense(*, session: Session, db_obj: Expense) -> None:
    session.delete(db_obj)
    session.commit()


# ============ Balance Calculation ============

def calculate_event_balances(*, session: Session, event_id: uuid.UUID) -> EventBalances:
    event = session.get(Event, event_id)
    members = get_event_members(session=session, event_id=event_id)
    member_ids = [m.user_id for m in members]
    users = {u.id: u for u in session.exec(select(User).where(User.id.in_(member_ids))).all()}

    expenses = get_expenses(session=session, event_id=event_id)

    paid = {uid: 0.0 for uid in member_ids}
    owed = {uid: 0.0 for uid in member_ids}

    for exp in expenses:
        paid[exp.payer_id] = paid.get(exp.payer_id, 0.0) + exp.amount
        for split in exp.splits:
            if not split.is_excluded:
                owed[split.user_id] = owed.get(split.user_id, 0.0) + split.amount_owed

    balances = []
    for uid in member_ids:
        user = users.get(uid)
        if user:
            balances.append(UserBalance(
                user_id=uid,
                user_email=user.email,
                user_full_name=user.full_name,
                total_paid=round(paid.get(uid, 0.0), 2),
                total_owed=round(owed.get(uid, 0.0), 2),
                net_balance=round(paid.get(uid, 0.0) - owed.get(uid, 0.0), 2)
            ))

    return EventBalances(
        event_id=event_id,
        event_name=event.name if event else "Unknown",
        balances=balances
    )


def calculate_my_balance_summary(*, session: Session, user_id: uuid.UUID) -> MyBalanceDetail:
    """Calculate what user owes across all events"""
    events = get_events(session=session, user_id=user_id)

    total_you_owe = 0.0
    total_owed_to_you = 0.0
    event_balances = []

    for event in events:
        eb = calculate_event_balances(session=session, event_id=event.id)
        event_balances.append(eb)

        # Find current user's balance in this event
        for bal in eb.balances:
            if bal.user_id == user_id:
                if bal.net_balance < 0:
                    total_you_owe += abs(bal.net_balance)
                else:
                    total_owed_to_you += bal.net_balance

    summary = MyBalanceSummary(
        total_you_owe=round(total_you_owe, 2),
        total_owed_to_you=round(total_owed_to_you, 2),
        net_balance=round(total_owed_to_you - total_you_owe, 2)
    )

    return MyBalanceDetail(events=event_balances, summary=summary)