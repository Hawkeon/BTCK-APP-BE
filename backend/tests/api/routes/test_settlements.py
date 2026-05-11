import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import Event, EventMember, Expense, ExpenseCreate, Settlement, SettlementCreate, User, UserCreate
from tests.utils.utils import random_email, random_lower_string


def create_event_with_members(
    session: Session, owner_id: uuid.UUID, member_ids: list[uuid.UUID]
) -> Event:
    event = crud.create_event(
        session=session,
        event_in=Event(name="Test Event", description="Test"),
        owner_id=owner_id,
    )
    for mid in member_ids:
        if mid != owner_id:
            crud.add_member(session=session, event_id=event.id, user_id=mid)
    return event


def create_expense(
    session: Session,
    event_id: uuid.UUID,
    payer_id: uuid.UUID,
    amount: float,
    member_ids: list[uuid.UUID],
) -> Expense:
    expense_in = ExpenseCreate(
        description="Test expense",
        amount=amount,
        expense_date=None,
        category="food",
        split_type="equal",
        include_user_ids=member_ids,
    )
    return crud.create_expense(
        session=session,
        expense_in=expense_in,
        event_id=event_id,
        payer_id=payer_id,
    )


def create_settlement_helper(
    session: Session,
    event_id: uuid.UUID,
    from_user_id: uuid.UUID,
    to_user_id: uuid.UUID,
    amount: float,
) -> Settlement:
    settlement_in = SettlementCreate(to_user_id=to_user_id, amount=amount)
    return crud.create_settlement(
        session=session,
        settlement_in=settlement_in,
        event_id=event_id,
        from_user_id=from_user_id,
    )


def test_create_settlement(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user_email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=db, user_create=UserCreate(email=user_email, password=password))

    user2_email = random_email()
    password2 = random_lower_string()
    user2 = crud.create_user(session=db, user_create=UserCreate(email=user2_email, password=password2))

    login_data = {"username": user_email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    event = create_event_with_members(session=db, owner_id=user.id, member_ids=[user.id, user2.id])

    create_expense(session=db, event_id=event.id, payer_id=user.id, amount=100.0, member_ids=[user.id, user2.id])

    settlement_data = {"to_user_id": str(user2.id), "amount": 50.0}
    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headers,
        json=settlement_data,
    )
    assert r.status_code == 200
    settlement = r.json()
    assert settlement["amount"] == 50.0
    assert settlement["from_user_id"] == str(user.id)
    assert settlement["to_user_id"] == str(user2.id)


def test_create_settlement_cannot_settle_with_self(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user_email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=db, user_create=UserCreate(email=user_email, password=password))

    user2_email = random_email()
    password2 = random_lower_string()
    user2 = crud.create_user(session=db, user_create=UserCreate(email=user2_email, password=password2))

    login_data = {"username": user_email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    event = create_event_with_members(session=db, owner_id=user.id, member_ids=[user.id, user2.id])

    settlement_data = {"to_user_id": str(user.id), "amount": 50.0}
    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headers,
        json=settlement_data,
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Cannot settle with yourself"


def test_create_settlement_recipient_not_member(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user_email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=db, user_create=UserCreate(email=user_email, password=password))

    user2_email = random_email()
    password2 = random_lower_string()
    user2 = crud.create_user(session=db, user_create=UserCreate(email=user2_email, password=password2))

    login_data = {"username": user_email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    event = crud.create_event(session=db, event_in=Event(name="Test", description="Test"), owner_id=user.id)

    settlement_data = {"to_user_id": str(user2.id), "amount": 50.0}
    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headers,
        json=settlement_data,
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Recipient must be an event member"


def test_list_settlements(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user_email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=db, user_create=UserCreate(email=user_email, password=password))

    user2_email = random_email()
    password2 = random_lower_string()
    user2 = crud.create_user(session=db, user_create=UserCreate(email=user2_email, password=password2))

    login_data = {"username": user_email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    event = create_event_with_members(session=db, owner_id=user.id, member_ids=[user.id, user2.id])

    create_settlement_helper(session=db, event_id=event.id, from_user_id=user.id, to_user_id=user2.id, amount=25.0)
    create_settlement_helper(session=db, event_id=event.id, from_user_id=user.id, to_user_id=user2.id, amount=25.0)

    r = client.get(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headers,
    )
    assert r.status_code == 200
    settlements = r.json()
    assert settlements["count"] == 2
    assert len(settlements["data"]) == 2


def test_get_settlement(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user_email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=db, user_create=UserCreate(email=user_email, password=password))

    user2_email = random_email()
    password2 = random_lower_string()
    user2 = crud.create_user(session=db, user_create=UserCreate(email=user2_email, password=password2))

    login_data = {"username": user_email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    event = create_event_with_members(session=db, owner_id=user.id, member_ids=[user.id, user2.id])

    settlement = create_settlement_helper(session=db, event_id=event.id, from_user_id=user.id, to_user_id=user2.id, amount=50.0)

    r = client.get(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/{settlement.id}",
        headers=headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["id"] == str(settlement.id)
    assert result["amount"] == 50.0


def test_get_settlement_not_found(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user_email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=db, user_create=UserCreate(email=user_email, password=password))

    event = crud.create_event(session=db, event_in=Event(name="Test", description="Test"), owner_id=user.id)

    login_data = {"username": user_email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/{uuid.uuid4()}",
        headers=headers,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Settlement not found"


def test_delete_settlement(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user_email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=db, user_create=UserCreate(email=user_email, password=password))

    user2_email = random_email()
    password2 = random_lower_string()
    user2 = crud.create_user(session=db, user_create=UserCreate(email=user2_email, password=password2))

    login_data = {"username": user_email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    event = create_event_with_members(session=db, owner_id=user.id, member_ids=[user.id, user2.id])

    settlement = create_settlement_helper(session=db, event_id=event.id, from_user_id=user.id, to_user_id=user2.id, amount=50.0)

    r = client.delete(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/{settlement.id}",
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Settlement deleted successfully"

    db.refresh(settlement)
    statement = select(Settlement).where(Settlement.id == settlement.id)
    assert db.exec(statement).first() is None


def test_delete_settlement_only_payer_can_delete(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user_email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=db, user_create=UserCreate(email=user_email, password=password))

    user2_email = random_email()
    password2 = random_lower_string()
    user2 = crud.create_user(session=db, user_create=UserCreate(email=user2_email, password=password2))

    login_data = {"username": user_email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    login_data2 = {"username": user2_email, "password": password2}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data2)
    token2 = r.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    event = create_event_with_members(session=db, owner_id=user.id, member_ids=[user.id, user2.id])

    settlement = create_settlement_helper(session=db, event_id=event.id, from_user_id=user.id, to_user_id=user2.id, amount=50.0)

    r = client.delete(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/{settlement.id}",
        headers=headers2,
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Only the payer can delete this settlement"


def test_settlement_affects_balance(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user_email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=db, user_create=UserCreate(email=user_email, password=password))

    user2_email = random_email()
    password2 = random_lower_string()
    user2 = crud.create_user(session=db, user_create=UserCreate(email=user2_email, password=password2))

    login_data = {"username": user_email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    event = create_event_with_members(session=db, owner_id=user.id, member_ids=[user.id, user2.id])

    create_expense(session=db, event_id=event.id, payer_id=user.id, amount=100.0, member_ids=[user.id, user2.id])

    balances_before = crud.calculate_event_balances_with_settlements(session=db, event_id=event.id)
    user_balance_before = next(b for b in balances_before.balances if b.user_id == user.id)
    user2_balance_before = next(b for b in balances_before.balances if b.user_id == user2.id)

    assert user_balance_before.net_balance == 50.0
    assert user2_balance_before.net_balance == -50.0

    settlement_data = {"to_user_id": str(user2.id), "amount": 25.0}
    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headers,
        json=settlement_data,
    )
    assert r.status_code == 200

    balances_after = crud.calculate_event_balances_with_settlements(session=db, event_id=event.id)
    user_balance_after = next(b for b in balances_after.balances if b.user_id == user.id)
    user2_balance_after = next(b for b in balances_after.balances if b.user_id == user2.id)

    assert user_balance_after.net_balance == 25.0
    assert user2_balance_after.net_balance == -25.0


def test_get_my_event_balance_with_settlements(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user_email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=db, user_create=UserCreate(email=user_email, password=password))

    user2_email = random_email()
    password2 = random_lower_string()
    user2 = crud.create_user(session=db, user_create=UserCreate(email=user2_email, password=password2))

    login_data = {"username": user_email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    event = create_event_with_members(session=db, owner_id=user.id, member_ids=[user.id, user2.id])

    create_expense(session=db, event_id=event.id, payer_id=user.id, amount=100.0, member_ids=[user.id, user2.id])
    create_settlement_helper(session=db, event_id=event.id, from_user_id=user.id, to_user_id=user2.id, amount=25.0)

    r = client.get(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/my/balances",
        headers=headers,
    )
    assert r.status_code == 200
    balances = r.json()
    user_balance = next(b for b in balances["balances"] if b["user_id"] == str(user.id))
    assert user_balance["net_balance"] == 25.0