import uuid
from datetime import date
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    Event,
    EventBalances,
    EventCreate,
    EventMember,
    EventStats,
    EventUpdate,
    Expense,
    ExpenseCreate,
    ExpenseSplit,
    ExpenseUpdate,
    InviteCode,
    MyBalanceDetail,
    MyBalanceSummary,
    Settlement,
    SettlementCreate,
    SimplifiedDebt,
    SimplifiedDebtsResponse,
    User,
    UserBalance,
    UserCreate,
    UserUpdate,
    UserFCMToken,
    Notification,
    NotificationType,
    get_datetime_utc,
)
from app.services.qr import generate_vietqr_url

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


def get_user_by_id(*, session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


def search_users_by_email(*, session: Session, email: str, current_user_id: uuid.UUID) -> list[User]:
    statement = select(User).where(
        User.email.ilike(f"%{email}%"),
        User.id != current_user_id
    )
    return session.exec(statement).all()


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

def create_event(*, session: Session, event_in: EventCreate, created_by_id: uuid.UUID) -> Event:
    db_obj = Event.model_validate(event_in, update={"created_by_id": created_by_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    # Auto-add creator as member
    member = EventMember(event_id=db_obj.id, user_id=created_by_id)
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
        .options(selectinload(Event.members), selectinload(Event.expenses))
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


def is_event_creator(*, session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    statement = select(Event).where(
        Event.id == event_id, Event.created_by_id == user_id
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

def add_member_by_user_id(*, session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> EventMember:
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


def add_member_by_email(*, session: Session, event_id: uuid.UUID, email: str) -> EventMember | None:
    user = get_user_by_email(session=session, email=email)
    if not user:
        return None
    return add_member_by_user_id(session=session, event_id=event_id, user_id=user.id)


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


def get_event_member_user(*, session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
    member = session.exec(
        select(EventMember).where(
            EventMember.event_id == event_id, EventMember.user_id == user_id
        )
    ).first()
    if not member:
        return None
    return session.get(User, user_id)


# ============ Expense CRUD ============

def create_expense(*, session: Session, expense_in: ExpenseCreate, event_id: uuid.UUID, created_by_id: uuid.UUID) -> Expense:
    db_obj = Expense(
        description=expense_in.description,
        amount=expense_in.amount,
        category=expense_in.category,
        expense_date=expense_in.expense_date or date.today(),
        event_id=event_id,
        payer_id=expense_in.payer_id,
        created_by_id=created_by_id,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)

    # Create splits
    for split_in in expense_in.splits:
        split = ExpenseSplit(
            expense_id=db_obj.id,
            user_id=split_in.user_id,
            amount_owed=split_in.amount_owed,
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
        .order_by(desc(Expense.expense_date), desc(Expense.created_at))
        .options(selectinload(Expense.payer), selectinload(Expense.splits).selectinload(ExpenseSplit.user))
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
    settlements = get_settlements(session=session, event_id=event_id)

    paid = dict.fromkeys(member_ids, 0)
    owed = dict.fromkeys(member_ids, 0)
    settled_from = dict.fromkeys(member_ids, 0)
    settled_to = dict.fromkeys(member_ids, 0)

    for exp in expenses:
        paid[exp.payer_id] = paid.get(exp.payer_id, 0) + exp.amount
        for split in exp.splits:
            owed[split.user_id] = owed.get(split.user_id, 0) + split.amount_owed

    for s in settlements:
        settled_from[s.from_user_id] = settled_from.get(s.from_user_id, 0) + s.amount
        settled_to[s.to_user_id] = settled_to.get(s.to_user_id, 0) + s.amount

    balances = []
    for uid in member_ids:
        user = users.get(uid)
        if user:
            net_before_settlements = paid.get(uid, 0) - owed.get(uid, 0)
            net_from_settlements = settled_from.get(uid, 0) - settled_to.get(uid, 0)
            net_balance = net_before_settlements + net_from_settlements

            balances.append(UserBalance(
                user_id=uid,
                user_email=user.email,
                user_full_name=user.full_name,
                bank_name=user.bank_name,
                account_number=user.account_number,
                account_holder=user.account_holder,
                total_paid=paid.get(uid, 0),
                total_owed=owed.get(uid, 0),
                net_balance=net_balance
            ))

    return EventBalances(
        event_id=event_id,
        event_name=event.name if event else "Unknown",
        balances=balances
    )


def calculate_my_balance_summary(*, session: Session, user_id: uuid.UUID) -> MyBalanceDetail:
    events = get_events(session=session, user_id=user_id)

    total_you_owe = 0
    total_owed_to_you = 0
    event_balances = []

    for event in events:
        eb = calculate_event_balances(session=session, event_id=event.id)
        event_balances.append(eb)

        for bal in eb.balances:
            if bal.user_id == user_id:
                if bal.net_balance < 0:
                    total_you_owe += abs(bal.net_balance)
                else:
                    total_owed_to_you += bal.net_balance

    summary = MyBalanceSummary(
        total_you_owe=total_you_owe,
        total_owed_to_you=total_owed_to_you,
        net_balance=total_owed_to_you - total_you_owe
    )

    return MyBalanceDetail(events=event_balances, summary=summary)


# ============ Settlement CRUD ============

def create_settlement(
    *, session: Session, settlement_in: SettlementCreate, event_id: uuid.UUID
) -> Settlement:
    db_obj = Settlement(
        event_id=event_id,
        from_user_id=settlement_in.from_user_id,
        to_user_id=settlement_in.to_user_id,
        amount=settlement_in.amount,
        note=settlement_in.note,
        idempotency_key=settlement_in.idempotency_key,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_settlement_by_idempotency_key(
    *, session: Session, idempotency_key: uuid.UUID
) -> Settlement | None:
    statement = select(Settlement).where(
        Settlement.idempotency_key == idempotency_key
    )
    return session.exec(statement).first()


def get_settlements(
    *, session: Session, event_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[Settlement]:
    statement = (
        select(Settlement)
        .where(Settlement.event_id == event_id)
        .offset(skip)
        .limit(limit)
        .order_by(Settlement.created_at.desc())
        .options(selectinload(Settlement.from_user), selectinload(Settlement.to_user))
    )
    return session.exec(statement).all()


def get_settlement(*, session: Session, settlement_id: uuid.UUID, event_id: uuid.UUID) -> Settlement | None:
    statement = select(Settlement).where(
        Settlement.id == settlement_id, Settlement.event_id == event_id
    )
    return session.exec(statement).first()


def delete_settlement(*, session: Session, db_obj: Settlement) -> None:
    session.delete(db_obj)
    session.commit()


def get_settlements_for_user_in_event(
    *, session: Session, event_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[list[Settlement], list[Settlement]]:
    all_settlements = get_settlements(session=session, event_id=event_id)
    made = [s for s in all_settlements if s.from_user_id == user_id]
    received = [s for s in all_settlements if s.to_user_id == user_id]
    return made, received


def calculate_event_balances_with_settlements(*, session: Session, event_id: uuid.UUID) -> EventBalances:
    return calculate_event_balances(session=session, event_id=event_id)


# ============ Invite Code CRUD ============

def generate_invite_code(*, session: Session, event_id: uuid.UUID, created_by_id: uuid.UUID, expires_in_hours: int | None = None, max_uses: int | None = None) -> InviteCode:
    import secrets
    code = secrets.token_urlsafe(8)[:12].upper()
    expires_at = None
    if expires_in_hours:
        from datetime import timedelta
        expires_at = get_datetime_utc() + timedelta(hours=expires_in_hours)

    db_obj = InviteCode(
        event_id=event_id,
        code=code,
        created_by_id=created_by_id,
        expires_at=expires_at,
        max_uses=max_uses,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_invite_code_by_code(*, session: Session, code: str) -> InviteCode | None:
    statement = select(InviteCode).where(InviteCode.code == code)
    return session.exec(statement).first()


def is_invite_code_valid(*, session: Session, code: str) -> bool:
    invite = get_invite_code_by_code(session=session, code=code)
    if not invite:
        return False
    if invite.expires_at and invite.expires_at < get_datetime_utc():
        return False
    if invite.max_uses and invite.use_count >= invite.max_uses:
        return False
    return True


def use_invite_code(*, session: Session, code: str) -> bool:
    invite = get_invite_code_by_code(session=session, code=code)
    if not invite:
        return False
    if not is_invite_code_valid(session=session, code=code):
        return False
    invite.use_count += 1
    session.add(invite)
    session.commit()
    return True


# ============ Simplify Debts Algorithm ============

def simplify_event_debts(*, session: Session, event_id: uuid.UUID) -> SimplifiedDebtsResponse:
    """Minimum cash flow algorithm to minimize number of transactions."""
    balances = calculate_event_balances(session=session, event_id=event_id)
    member_ids = [b.user_id for b in balances.balances]
    users = {b.user_id: b for b in balances.balances}

    # Calculate net balance for each user
    net = {}
    for bal in balances.balances:
        net[bal.user_id] = bal.net_balance

    # Separate creditors (positive) and debtors (negative)
    creditors = [(uid, net[uid]) for uid in member_ids if net[uid] > 0]
    debtors = [(uid, -net[uid]) for uid in member_ids if net[uid] < 0]

    # Sort by absolute amount descending
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    debts = []
    i, j = 0, 0
    while i < len(creditors) and j < len(debtors):
        creditor_id, credit_amount = creditors[i]
        debtor_id, debt_amount = debtors[j]

        # Settle the minimum of the two
        settle_amount = min(credit_amount, debt_amount)
        if settle_amount > 0:
            creditor = users.get(creditor_id)
            debtor = users.get(debtor_id)
            if creditor and debtor:
                debts.append(SimplifiedDebt(
                    from_user_id=debtor_id,
                    from_user_email=debtor.user_email,
                    from_user_full_name=debtor.user_full_name,
                    to_user_id=creditor_id,
                    to_user_email=creditor.user_email,
                    to_user_full_name=creditor.user_full_name,
                    amount=settle_amount
                ))

        # Update remaining amounts
        creditors[i] = (creditor_id, credit_amount - settle_amount)
        debtors[j] = (debtor_id, debt_amount - settle_amount)

        if creditors[i][1] <= 0:
            i += 1
        if debtors[j][1] <= 0:
            j += 1

    return SimplifiedDebtsResponse(event_id=event_id, debts=debts)


# ============ Event Stats ============

def get_event_stats(*, session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> EventStats:
    balances = calculate_event_balances(session=session, event_id=event_id)
    expenses = get_expenses(session=session, event_id=event_id)
    members = get_event_members(session=session, event_id=event_id)

    total_spent = sum(e.amount for e in expenses)

    user_balance = None
    for bal in balances.balances:
        if bal.user_id == user_id:
            user_balance = bal
            break

    return EventStats(
        event_id=event_id,
        total_spent=total_spent,
        expense_count=len(expenses),
        member_count=len(members),
        your_total_paid=user_balance.total_paid if user_balance else 0,
        your_total_owed=user_balance.total_owed if user_balance else 0,
        your_net_balance=user_balance.net_balance if user_balance else 0,
    )


# ============ Notification CRUD ============

def create_notification(
    *,
    session: Session,
    recipient_id: uuid.UUID,
    title: str,
    content: str,
    type: NotificationType,
    sender_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
    reference_id: uuid.UUID | None = None
) -> Notification:
    db_obj = Notification(
        recipient_id=recipient_id,
        sender_id=sender_id,
        event_id=event_id,
        title=title,
        content=content,
        type=type,
        reference_id=reference_id
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)

    # Trigger FCM Push
    try:
        from app.services.fcm import fcm_service
        token_statement = select(UserFCMToken).where(UserFCMToken.user_id == recipient_id)
        tokens = [t.fcm_token for t in session.exec(token_statement).all()]
        if tokens:
            fcm_service.send_push(
                tokens=tokens,
                title=title,
                body=content,
                data={
                    "type": type.value,
                    "event_id": str(event_id) if event_id else "",
                    "reference_id": str(reference_id) if reference_id else ""
                }
            )
    except Exception as e:
        print(f"Error triggering FCM push: {e}")

    return db_obj


def get_notifications(*, session: Session, recipient_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[Notification]:
    statement = (
        select(Notification)
        .where(Notification.recipient_id == recipient_id)
        .offset(skip)
        .limit(limit)
        .order_by(desc(Notification.created_at))
    )
    return session.exec(statement).all()


def get_notification(*, session: Session, notification_id: uuid.UUID, recipient_id: uuid.UUID) -> Notification | None:
    statement = select(Notification).where(
        Notification.id == notification_id,
        Notification.recipient_id == recipient_id
    )
    return session.exec(statement).first()


def mark_notification_as_read(*, session: Session, db_obj: Notification) -> Notification:
    db_obj.is_read = True
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def mark_all_notifications_as_read(*, session: Session, recipient_id: uuid.UUID) -> int:
    from sqlmodel import update
    statement = select(Notification).where(
        Notification.recipient_id == recipient_id,
        Notification.is_read == False
    )
    notifications = session.exec(statement).all()
    for n in notifications:
        n.is_read = True
        session.add(n)
    session.commit()
    return len(notifications)
