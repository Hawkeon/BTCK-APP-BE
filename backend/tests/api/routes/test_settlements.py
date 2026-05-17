import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import (
    Event,
    EventCreate,
    ExpenseCreate,
    ExpenseSplitCreate,
    Settlement,
    SettlementCreate,
    User,
    UserCreate,
)
from tests.utils.utils import random_email, random_lower_string


def _create_user(session: Session) -> tuple[User, str, str]:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(session=session, user_create=UserCreate(email=email, password=password))
    return user, email, password


def _auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    r = client.post(f"{settings.API_V1_STR}/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_event_with_members(session: Session, owner_id: uuid.UUID, member_ids: list[uuid.UUID]) -> Event:
    event = crud.create_event(
        session=session, event_in=EventCreate(name="Test Event", description="Test"), created_by_id=owner_id,
    )
    for mid in member_ids:
        if mid != owner_id:
            crud.add_member_by_user_id(session=session, event_id=event.id, user_id=mid)
    return event


def _create_expense(
    session: Session,
    event_id: uuid.UUID,
    created_by_id: uuid.UUID,
    payer_id: uuid.UUID,
    amount: int,
    splits: list[tuple[uuid.UUID, int]],
) -> crud.Expense:
    expense_in = ExpenseCreate(
        description="Test expense",
        amount=amount,
        category="food",
        payer_id=payer_id,
        splits=[ExpenseSplitCreate(user_id=uid, amount_owed=amt) for uid, amt in splits],
    )
    return crud.create_expense(
        session=session, expense_in=expense_in, event_id=event_id, created_by_id=created_by_id,
    )


# ============ Basic CRUD Tests ============


def test_create_settlement(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user1, email1, pw1 = _create_user(db)
    user2, email2, pw2 = _create_user(db)

    event = _create_event_with_members(db, user1.id, [user1.id, user2.id])
    _create_expense(db, event.id, user1.id, user1.id, 100000, [(user2.id, 50000)])

    settlement_data = {
        "from_user_id": str(user2.id),
        "to_user_id": str(user1.id),
        "amount": 40000,
        "idempotency_key": str(uuid.uuid4()),
    }
    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=_auth_headers(client, email2, pw2),
        json=settlement_data,
    )
    assert r.status_code == 200
    s = r.json()
    assert s["amount"] == 40000
    assert s["from_user_id"] == str(user2.id)
    assert s["to_user_id"] == str(user1.id)
    assert "idempotency_key" in s


def test_missing_idempotency_key_returns_422(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user1, email1, pw1 = _create_user(db)
    user2, _, _ = _create_user(db)
    headers = _auth_headers(client, email1, pw1)

    event = _create_event_with_members(db, user1.id, [user1.id, user2.id])
    _create_expense(db, event.id, user1.id, user1.id, 100000, [(user2.id, 50000)])

    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headers,
        json={"from_user_id": str(user1.id), "to_user_id": str(user2.id), "amount": 30000},
    )
    assert r.status_code == 422
    errors = r.json()["detail"]
    assert any(
        e["loc"] == ["body", "idempotency_key"] and e["type"] == "missing"
        for e in errors
    )

    # No settlement created
    settlements = crud.get_settlements(session=db, event_id=event.id)
    assert len(settlements) == 0


def test_create_settlement_cannot_settle_with_self(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user1, email1, pw1 = _create_user(db)
    user2, _, _ = _create_user(db)
    headers = _auth_headers(client, email1, pw1)

    event = _create_event_with_members(db, user1.id, [user1.id, user2.id])
    _create_expense(db, event.id, user1.id, user1.id, 100000, [(user2.id, 50000)])

    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headers,
        json={"from_user_id": str(user1.id), "to_user_id": str(user1.id), "amount": 50000, "idempotency_key": str(uuid.uuid4())},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Cannot settle with yourself"


def test_create_settlement_wrong_from_user(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user1, email1, pw1 = _create_user(db)
    user2, email2, pw2 = _create_user(db)
    headers1 = _auth_headers(client, email1, pw1)

    event = _create_event_with_members(db, user1.id, [user1.id, user2.id])
    _create_expense(db, event.id, user1.id, user1.id, 100000, [(user2.id, 50000)])

    # user1 tries to send settlement as user2 (wrong from_user_id for auth token)
    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headers1,
        json={"from_user_id": str(user2.id), "to_user_id": str(user1.id), "amount": 50000, "idempotency_key": str(uuid.uuid4())},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "from_user_id must be current user"


def test_create_settlement_recipient_not_member(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user1, email1, pw1 = _create_user(db)
    user2, _, _ = _create_user(db)
    headers = _auth_headers(client, email1, pw1)

    event = crud.create_event(session=db, event_in=EventCreate(name="Test", description="Test"), created_by_id=user1.id)

    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headers,
        json={"from_user_id": str(user1.id), "to_user_id": str(user2.id), "amount": 50000, "idempotency_key": str(uuid.uuid4())},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "to_user_id must be an event member"


def test_list_settlements(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user1, email1, pw1 = _create_user(db)
    user2, _, _ = _create_user(db)
    headers = _auth_headers(client, email1, pw1)

    event = _create_event_with_members(db, user1.id, [user1.id, user2.id])
    _create_expense(db, event.id, user1.id, user2.id, 100000, [(user2.id, 100000)])

    # Create 2 settlements
    crud.create_settlement(
        session=db,
        settlement_in=SettlementCreate(from_user_id=user2.id, to_user_id=user1.id, amount=40000, idempotency_key=uuid.uuid4()),
        event_id=event.id,
    )
    crud.create_settlement(
        session=db,
        settlement_in=SettlementCreate(from_user_id=user2.id, to_user_id=user1.id, amount=60000, idempotency_key=uuid.uuid4()),
        event_id=event.id,
    )

    r = client.get(f"{settings.API_V1_STR}/events/{event.id}/settlements/", headers=headers)
    assert r.status_code == 200
    result = r.json()
    assert result["count"] == 2
    assert len(result["data"]) == 2


def test_get_settlement(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user1, email1, pw1 = _create_user(db)
    user2, _, _ = _create_user(db)
    headers = _auth_headers(client, email1, pw1)

    event = _create_event_with_members(db, user1.id, [user1.id, user2.id])
    _create_expense(db, event.id, user1.id, user2.id, 100000, [(user2.id, 100000)])

    s = crud.create_settlement(
        session=db,
        settlement_in=SettlementCreate(from_user_id=user2.id, to_user_id=user1.id, amount=50000, idempotency_key=uuid.uuid4()),
        event_id=event.id,
    )

    r = client.get(f"{settings.API_V1_STR}/events/{event.id}/settlements/{s.id}", headers=headers)
    assert r.status_code == 200
    result = r.json()
    assert result["id"] == str(s.id)
    assert result["amount"] == 50000


def test_get_settlement_not_found(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user1, email1, pw1 = _create_user(db)
    headers = _auth_headers(client, email1, pw1)

    event = crud.create_event(session=db, event_in=EventCreate(name="Test", description="Test"), created_by_id=user1.id)

    r = client.get(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/{uuid.uuid4()}",
        headers=headers,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Settlement not found"


def test_delete_settlement(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user1, email1, pw1 = _create_user(db)
    user2, email2, pw2 = _create_user(db)
    headers = _auth_headers(client, email2, pw2)

    event = _create_event_with_members(db, user1.id, [user1.id, user2.id])
    _create_expense(db, event.id, user1.id, user2.id, 100000, [(user2.id, 100000)])

    s = crud.create_settlement(
        session=db,
        settlement_in=SettlementCreate(from_user_id=user2.id, to_user_id=user1.id, amount=50000, idempotency_key=uuid.uuid4()),
        event_id=event.id,
    )

    settlement_id = s.id
    r = client.delete(f"{settings.API_V1_STR}/events/{event.id}/settlements/{settlement_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["message"] == "Settlement deleted successfully"

    db.expire_all()
    statement = select(Settlement).where(Settlement.id == settlement_id)
    assert db.exec(statement).first() is None


def test_delete_settlement_only_payer_can_delete(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    user1, email1, pw1 = _create_user(db)
    user2, email2, pw2 = _create_user(db)
    headers1 = _auth_headers(client, email1, pw1)

    event = _create_event_with_members(db, user1.id, [user1.id, user2.id])
    _create_expense(db, event.id, user1.id, user2.id, 100000, [(user2.id, 100000)])

    s = crud.create_settlement(
        session=db,
        settlement_in=SettlementCreate(from_user_id=user2.id, to_user_id=user1.id, amount=50000, idempotency_key=uuid.uuid4()),
        event_id=event.id,
    )

    # user1 (creditor) tries to delete
    r = client.delete(f"{settings.API_V1_STR}/events/{event.id}/settlements/{s.id}", headers=headers1)
    assert r.status_code == 403
    assert r.json()["detail"] == "Only the payer can delete this settlement"


# ============ Balance Formula Tests ============


def test_balance_partial_settlement(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    """A pays 100K, split with B (50K each). B settles 40K to A. Check balances."""
    userA, emailA, pwA = _create_user(db)
    userB, emailB, pwB = _create_user(db)
    headersB = _auth_headers(client, emailB, pwB)

    event = _create_event_with_members(db, userA.id, [userA.id, userB.id])
    _create_expense(db, event.id, userA.id, userA.id, 100000, [(userA.id, 50000), (userB.id, 50000)])

    balances_before = crud.calculate_event_balances(session=db, event_id=event.id)
    balA_before = next(b for b in balances_before.balances if b.user_id == userA.id)
    balB_before = next(b for b in balances_before.balances if b.user_id == userB.id)
    assert balA_before.net_balance == 50000  # A paid 100K, owes 50K = +50K
    assert balB_before.net_balance == -50000  # B owes 50K

    # B settles 40K to A
    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headersB,
        json={"from_user_id": str(userB.id), "to_user_id": str(userA.id), "amount": 40000, "idempotency_key": str(uuid.uuid4())},
    )
    assert r.status_code == 200

    balances_after = crud.calculate_event_balances(session=db, event_id=event.id)
    balA_after = next(b for b in balances_after.balances if b.user_id == userA.id)
    balB_after = next(b for b in balances_after.balances if b.user_id == userB.id)
    assert balA_after.net_balance == 10000  # 50K - 40K received = 10K
    assert balB_after.net_balance == -10000  # -50K + 40K paid = -10K


def test_balance_full_settlement(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    """A pays 100K, split with B (50K each). B settles full 50K to A."""
    userA, emailA, pwA = _create_user(db)
    userB, emailB, pwB = _create_user(db)
    headersB = _auth_headers(client, emailB, pwB)

    event = _create_event_with_members(db, userA.id, [userA.id, userB.id])
    _create_expense(db, event.id, userA.id, userA.id, 100000, [(userA.id, 50000), (userB.id, 50000)])

    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headersB,
        json={"from_user_id": str(userB.id), "to_user_id": str(userA.id), "amount": 50000, "idempotency_key": str(uuid.uuid4())},
    )
    assert r.status_code == 200

    balances = crud.calculate_event_balances(session=db, event_id=event.id)
    balA = next(b for b in balances.balances if b.user_id == userA.id)
    balB = next(b for b in balances.balances if b.user_id == userB.id)
    assert balA.net_balance == 0
    assert balB.net_balance == 0


# ============ Idempotency Tests ============


def test_duplicate_idempotency_key(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    """Same idempotency_key sent multiple times = only one settlement, balance correct."""
    userA, emailA, pwA = _create_user(db)
    userB, emailB, pwB = _create_user(db)
    headersB = _auth_headers(client, emailB, pwB)

    event = _create_event_with_members(db, userA.id, [userA.id, userB.id])
    _create_expense(db, event.id, userA.id, userA.id, 100000, [(userA.id, 50000), (userB.id, 50000)])

    idem_key = str(uuid.uuid4())
    payload = {
        "from_user_id": str(userB.id),
        "to_user_id": str(userA.id),
        "amount": 40000,
        "idempotency_key": idem_key,
    }

    # Send 10 times with same idempotency_key
    responses = [
        client.post(
            f"{settings.API_V1_STR}/events/{event.id}/settlements/",
            headers=headersB,
            json=payload,
        )
        for _ in range(10)
    ]

    # All should return 200
    for i, r in enumerate(responses):
        assert r.status_code == 200, f"Request {i} failed: {r.json()}"

    # All should return the same settlement id
    settlement_ids = {r.json()["id"] for r in responses}
    assert len(settlement_ids) == 1

    # Only one row in DB
    settlements_in_db = crud.get_settlements(session=db, event_id=event.id)
    assert len(settlements_in_db) == 1

    # Balance reduced only once
    balances = crud.calculate_event_balances(session=db, event_id=event.id)
    balA = next(b for b in balances.balances if b.user_id == userA.id)
    balB = next(b for b in balances.balances if b.user_id == userB.id)
    assert balA.net_balance == 10000  # 50K - 40K = 10K
    assert balB.net_balance == -10000  # -50K + 40K = -10K


def test_idempotency_key_unique_across_payloads(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    """Different payloads with different idempotency_key each create a settlement."""
    userA, emailA, pwA = _create_user(db)
    userB, emailB, pwB = _create_user(db)
    headersB = _auth_headers(client, emailB, pwB)

    event = _create_event_with_members(db, userA.id, [userA.id, userB.id])
    _create_expense(db, event.id, userA.id, userA.id, 100000, [(userA.id, 50000), (userB.id, 50000)])

    r1 = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headersB,
        json={
            "from_user_id": str(userB.id),
            "to_user_id": str(userA.id),
            "amount": 20000,
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    assert r1.status_code == 200

    r2 = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headersB,
        json={
            "from_user_id": str(userB.id),
            "to_user_id": str(userA.id),
            "amount": 20000,
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    assert r2.status_code == 200
    assert r1.json()["id"] != r2.json()["id"]

    settlements_in_db = crud.get_settlements(session=db, event_id=event.id)
    assert len(settlements_in_db) == 2

    balances = crud.calculate_event_balances(session=db, event_id=event.id)
    balB = next(b for b in balances.balances if b.user_id == userB.id)
    assert balB.net_balance == -10000  # -50K + 20K + 20K = -10K


# ============ Amount Validation Tests ============


def test_over_settlement_rejected(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    """B owes A 50K but tries to settle 60K. Rejected."""
    userA, emailA, pwA = _create_user(db)
    userB, emailB, pwB = _create_user(db)
    headersB = _auth_headers(client, emailB, pwB)

    event = _create_event_with_members(db, userA.id, [userA.id, userB.id])
    _create_expense(db, event.id, userA.id, userA.id, 100000, [(userA.id, 50000), (userB.id, 50000)])

    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headersB,
        json={"from_user_id": str(userB.id), "to_user_id": str(userA.id), "amount": 60000, "idempotency_key": str(uuid.uuid4())},
    )
    assert r.status_code == 400
    assert "exceeds remaining debt" in r.json()["detail"]

    # No settlement created
    settlements = crud.get_settlements(session=db, event_id=event.id)
    assert len(settlements) == 0

    # Balance unchanged
    balances = crud.calculate_event_balances(session=db, event_id=event.id)
    balB = next(b for b in balances.balances if b.user_id == userB.id)
    assert balB.net_balance == -50000


def test_wrong_direction_rejected(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    """A is creditor. A tries settlement A -> B. Rejected because A does not owe B."""
    userA, emailA, pwA = _create_user(db)
    userB, emailB, pwB = _create_user(db)
    headersA = _auth_headers(client, emailA, pwA)

    event = _create_event_with_members(db, userA.id, [userA.id, userB.id])
    _create_expense(db, event.id, userA.id, userA.id, 100000, [(userA.id, 50000), (userB.id, 50000)])

    # A tries to settle to B (wrong direction — A doesn't owe B)
    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headersA,
        json={"from_user_id": str(userA.id), "to_user_id": str(userB.id), "amount": 10000, "idempotency_key": str(uuid.uuid4())},
    )
    assert r.status_code == 400
    assert "No debt owed" in r.json()["detail"]

    # No settlement created
    settlements = crud.get_settlements(session=db, event_id=event.id)
    assert len(settlements) == 0


def test_settlement_amount_zero_rejected(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    userA, emailA, pwA = _create_user(db)
    userB, emailB, pwB = _create_user(db)
    headersB = _auth_headers(client, emailB, pwB)

    event = _create_event_with_members(db, userA.id, [userA.id, userB.id])
    _create_expense(db, event.id, userA.id, userA.id, 100000, [(userA.id, 50000), (userB.id, 50000)])

    r = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headersB,
        json={"from_user_id": str(userB.id), "to_user_id": str(userA.id), "amount": 0, "idempotency_key": str(uuid.uuid4())},
    )
    assert r.status_code == 422  # Pydantic validation error


def test_my_balance_endpoint_with_settlements(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    userA, emailA, pwA = _create_user(db)
    userB, emailB, pwB = _create_user(db)
    headersB = _auth_headers(client, emailB, pwB)

    event = _create_event_with_members(db, userA.id, [userA.id, userB.id])
    _create_expense(db, event.id, userA.id, userA.id, 100000, [(userA.id, 50000), (userB.id, 50000)])

    # B settles 25K to A
    client.post(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/",
        headers=headersB,
        json={"from_user_id": str(userB.id), "to_user_id": str(userA.id), "amount": 25000, "idempotency_key": str(uuid.uuid4())},
    )

    r = client.get(
        f"{settings.API_V1_STR}/events/{event.id}/settlements/my/balances",
        headers=headersB,
    )
    assert r.status_code == 200
    balances = r.json()
    userB_balance = next(b for b in balances["balances"] if b["user_id"] == str(userB.id))
    assert userB_balance["net_balance"] == -25000  # -50K + 25K = -25K
