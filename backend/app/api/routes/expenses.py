import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ExpenseCreate,
    ExpensePublic,
    ExpenseSplitPublic,
    ExpensesPublic,
    ExpenseUpdate,
    Message,
    NotificationType,
)

router = APIRouter(prefix="/events/{event_id}/expenses", tags=["expenses"])


def expense_to_public(expense, _session: SessionDep) -> ExpensePublic:
    payer = expense.payer
    splits = [
        ExpenseSplitPublic(
            user_id=s.user_id,
            amount_owed=s.amount_owed,
            user_email=s.user.email if s.user else None,
            user_full_name=s.user.full_name if s.user else None,
            user_qr_code_url=s.user.qr_code_url if s.user else None,
        )
        for s in expense.splits
    ]
    return ExpensePublic(
        id=expense.id,
        description=expense.description,
        amount=expense.amount,
        category=expense.category,
        image_url=expense.image_url,
        expense_date=expense.expense_date,
        event_id=expense.event_id,
        created_by_id=expense.created_by_id,
        payer_id=expense.payer_id,
        created_at=expense.created_at,
        payer_email=payer.email if payer else None,
        payer_full_name=payer.full_name if payer else None,
        splits=splits
    )


def check_event_access(event_id: uuid.UUID, session, current_user: CurrentUser) -> None:
    event = crud.get_event(session=session, event_id=event_id, user_id=current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")


@router.get("/", response_model=ExpensesPublic)
def list_expenses(
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> ExpensesPublic:
    check_event_access(event_id, session, current_user)
    expenses = crud.get_expenses(session=session, event_id=event_id, skip=skip, limit=limit)
    expense_list = [expense_to_public(e, session) for e in expenses]
    return ExpensesPublic(data=expense_list, count=len(expense_list))


@router.post("/", response_model=ExpensePublic)
def create_expense(
    event_id: uuid.UUID,
    expense_in: ExpenseCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ExpensePublic:
    check_event_access(event_id, session, current_user)

    # Validate: current user must be an event member
    if not crud.is_event_member(session=session, event_id=event_id, user_id=current_user.id):
        raise HTTPException(status_code=403, detail="You are not a member of this event")

    # Validate: payer_id must be an event member
    if not crud.is_event_member(session=session, event_id=event_id, user_id=expense_in.payer_id):
        raise HTTPException(status_code=400, detail="Payer must be an event member")

    # Validate: all split user_ids must be event members
    member_ids = set(crud.get_event_member_ids(session=session, event_id=event_id))
    for split in expense_in.splits:
        if split.user_id not in member_ids:
            raise HTTPException(status_code=400, detail=f"User {split.user_id} is not a member of this event")

    # Validate: sum of splits must equal total amount
    total_splits = sum(s.amount_owed for s in expense_in.splits)
    if total_splits != expense_in.amount:
        raise HTTPException(status_code=400, detail="Split amounts must equal total amount")

    expense = crud.create_expense(
        session=session,
        expense_in=expense_in,
        event_id=event_id,
        created_by_id=current_user.id,
    )

    # Send notifications to other members
    members = crud.get_event_members(session=session, event_id=event_id)
    event = session.get(crud.Event, event_id)
    for member in members:
        if member.user_id != current_user.id:
            crud.create_notification(
                session=session,
                recipient_id=member.user_id,
                sender_id=current_user.id,
                event_id=event_id,
                title="Khoản chi mới",
                content=f"{current_user.full_name or current_user.email} đã thêm khoản chi '{expense.description}' {expense.amount:,}đ trong nhóm '{event.name if event else ''}'",
                type=NotificationType.EXPENSE_CREATED,
                reference_id=expense.id
            )

    return expense_to_public(expense, session)


@router.get("/{expense_id}", response_model=ExpensePublic)
def get_expense(
    event_id: uuid.UUID,
    expense_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> ExpensePublic:
    check_event_access(event_id, session, current_user)
    expense = crud.get_expense(session=session, expense_id=expense_id, event_id=event_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense_to_public(expense, session)


@router.put("/{expense_id}", response_model=ExpensePublic)
def update_expense(
    event_id: uuid.UUID,
    expense_id: uuid.UUID,
    expense_in: ExpenseUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ExpensePublic:
    check_event_access(event_id, session, current_user)
    expense = crud.get_expense(session=session, expense_id=expense_id, event_id=event_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only creator can update expense")
    expense = crud.update_expense(session=session, db_obj=expense, obj_in=expense_in)
    return expense_to_public(expense, session)


@router.delete("/{expense_id}", response_model=Message)
def delete_expense(
    event_id: uuid.UUID,
    expense_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Message:
    check_event_access(event_id, session, current_user)
    expense = crud.get_expense(session=session, expense_id=expense_id, event_id=event_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only creator can delete expense")
    crud.delete_expense(session=session, db_obj=expense)
    return Message(message="Expense deleted successfully")


@router.post("/{expense_id}/image", response_model=ExpensePublic)
async def upload_expense_image(
    event_id: uuid.UUID,
    expense_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> ExpensePublic:
    """Upload an image for an expense as visual reminder."""
    check_event_access(event_id, session, current_user)
    expense = crud.get_expense(session=session, expense_id=expense_id, event_id=event_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: JPEG, PNG, GIF, WebP")

    # Create uploads directory if not exists
    upload_dir = "/app/uploads/expense_images"
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    file_ext = file.filename.split(".")[-1] if file.filename else "png"
    filename = f"{expense_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    file_path = os.path.join(upload_dir, filename)

    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Update expense image_url
    image_url = f"/uploads/expense_images/{filename}"
    expense.image_url = image_url
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense_to_public(expense, session)
