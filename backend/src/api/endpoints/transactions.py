"""
Transaction Management API Endpoints
Handles borrowing, returning, and employee request operations
"""

import math
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.qr_generator import qr_generator
from src.core.security import get_current_admin_user, get_current_user
from src.models.item import Item, ItemStatus
from src.models.transaction import Request, Transaction, TransactionStatus
from src.models.user import User
from src.schemas.transaction_schema import (
    RequestCreate,
    RequestDetailResponse,
    RequestListResponse,
    RequestUpdate,
    TransactionCreate,
    TransactionDetailResponse,
    TransactionListResponse,
    TransactionReturn,
)

router = APIRouter(tags=["Transactions"])


# ============================================================================
# BORROWING ENDPOINTS
# ============================================================================

@router.post("/borrow", response_model=TransactionDetailResponse, status_code=status.HTTP_201_CREATED)
async def borrow_item(
        transaction_data: TransactionCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Borrow an item using QR codes.

    user_qr_code is OPTIONAL:
    - Omitted → borrow for the authenticated user themselves (self-borrow).
    - Provided → admin assigns borrow to that user (requires is_admin).
    """
    # ── Resolve BORROWER ─────────────────────────────────────────────────────
    if transaction_data.user_qr_code:
        # Admin is assigning the borrow to a specific user via their QR card.
        user_qr = qr_generator.parse_qr_data(transaction_data.user_qr_code)
        if not user_qr or user_qr["type"] != "user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user QR code format. Please scan a valid user QR code."
            )
        user = db.query(User).filter(User.id == user_qr["id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_qr['id']} not found"
            )
        # Only admins may borrow on behalf of another user.
        if user.id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can borrow items on behalf of another user"
            )
    else:
        # No user QR provided → borrow for the authenticated user themselves.
        user = current_user

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive and cannot borrow items"
        )

    # ── Resolve ITEM ─────────────────────────────────────────────────────────
    item_qr = qr_generator.parse_qr_data(transaction_data.item_qr_code)
    if not item_qr or item_qr["type"] != "item":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item QR code format. Please scan a valid item QR code."
        )

    item = db.query(Item).filter(Item.id == item_qr["id"]).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_qr['id']} not found"
        )

    if not item.is_borrowable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{item.name}' is not available for borrowing"
        )

    if item.status not in [ItemStatus.AVAILABLE]:
        status_messages = {
            ItemStatus.BORROWED: "currently borrowed",
            ItemStatus.MAINTENANCE: "under maintenance",
            ItemStatus.RETIRED: "retired and no longer available"
        }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Item is {status_messages.get(item.status, 'not available')}"
        )

    if item.available_quantity < transaction_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient quantity. Only {item.available_quantity} of {item.quantity} available"
        )

    # Calculate due date
    due_date = None
    if transaction_data.due_days:
        due_date = datetime.now(UTC) + timedelta(days=transaction_data.due_days)
    elif item.max_borrow_days:
        due_date = datetime.now(UTC) + timedelta(days=item.max_borrow_days)
    else:
        due_date = datetime.now(UTC) + timedelta(days=7)

    new_transaction = Transaction(
        user_id=user.id,
        item_id=item.id,
        quantity=transaction_data.quantity,
        status=TransactionStatus.BORROWED,
        purpose=transaction_data.purpose,
        notes=transaction_data.notes,
        due_date=due_date,
        condition_at_borrow="good"
    )

    item.available_quantity -= transaction_data.quantity

    if item.available_quantity == 0:
        item.status = ItemStatus.BORROWED

    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return TransactionDetailResponse(
        id=new_transaction.id,
        user_id=new_transaction.user_id,
        item_id=new_transaction.item_id,
        status=new_transaction.status,
        quantity=new_transaction.quantity,
        borrowed_at=new_transaction.borrowed_at,
        due_date=new_transaction.due_date,
        returned_at=new_transaction.returned_at,
        purpose=new_transaction.purpose,
        notes=new_transaction.notes,
        condition_at_borrow=new_transaction.condition_at_borrow,
        condition_at_return=new_transaction.condition_at_return,
        created_at=new_transaction.created_at,
        updated_at=new_transaction.updated_at,
        user_name=user.full_name,
        user_email=user.email,
        item_name=item.name,
        item_code=item.item_code
    )


@router.post("/return", response_model=TransactionDetailResponse)
async def return_item(
        return_data: TransactionReturn,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Return a borrowed item.

    Workflow:
    1. Locate the transaction
    2. Verify ownership (or admin)
    3. Mark as returned
    4. Update item availability
    5. Record condition and notes
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == return_data.transaction_id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {return_data.transaction_id} not found"
        )

    if transaction.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to return this item"
        )

    if transaction.status != TransactionStatus.BORROWED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This item is not currently borrowed (status: {transaction.status.value})"
        )

    item = db.query(Item).filter(Item.id == transaction.item_id).first()
    user = db.query(User).filter(User.id == transaction.user_id).first()

    if not item or not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Associated item or user not found"
        )

    transaction.status = TransactionStatus.RETURNED
    transaction.returned_at = datetime.now(UTC)
    transaction.condition_at_return = return_data.condition_at_return or "good"

    if return_data.notes:
        if transaction.notes:
            transaction.notes += f"\n[Return] {return_data.notes}"
        else:
            transaction.notes = f"[Return] {return_data.notes}"

    item.available_quantity += transaction.quantity

    if item.status == ItemStatus.BORROWED and item.available_quantity > 0:
        item.status = ItemStatus.AVAILABLE

    db.commit()
    db.refresh(transaction)

    return TransactionDetailResponse(
        id=transaction.id,
        user_id=transaction.user_id,
        item_id=transaction.item_id,
        status=transaction.status,
        quantity=transaction.quantity,
        borrowed_at=transaction.borrowed_at,
        due_date=transaction.due_date,
        returned_at=transaction.returned_at,
        purpose=transaction.purpose,
        notes=transaction.notes,
        condition_at_borrow=transaction.condition_at_borrow,
        condition_at_return=transaction.condition_at_return,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        user_name=user.full_name,
        user_email=user.email,
        item_name=item.name,
        item_code=item.item_code
    )


# ============================================================================
# TRANSACTION LISTING AND QUERIES
# ============================================================================

@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(50, ge=1, le=100, description="Items per page"),
        status: TransactionStatus | None = Query(None, description="Filter by status"),
        user_id: int | None = Query(None, description="Filter by user ID (admin only)"),
        item_id: int | None = Query(None, description="Filter by item ID"),
        overdue_only: bool = Query(False, description="Show only overdue items"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get paginated list of transactions.
    Regular users see only their own. Admins see all.
    """
    query = db.query(Transaction)

    if not current_user.is_admin:
        query = query.filter(Transaction.user_id == current_user.id)
    else:
        if user_id:
            query = query.filter(Transaction.user_id == user_id)

    if item_id:
        query = query.filter(Transaction.item_id == item_id)

    if status:
        query = query.filter(Transaction.status == status)

    if overdue_only:
        query = query.filter(
            Transaction.status == TransactionStatus.BORROWED,
            Transaction.due_date < datetime.now(UTC)
        )

    total = query.count()
    offset = (page - 1) * page_size
    transactions = query.order_by(Transaction.created_at.desc()).offset(offset).limit(page_size).all()

    detailed_transactions = []
    for trans in transactions:
        user = db.query(User).filter(User.id == trans.user_id).first()
        item = db.query(Item).filter(Item.id == trans.item_id).first()

        detailed_transactions.append(TransactionDetailResponse(
            id=trans.id,
            user_id=trans.user_id,
            item_id=trans.item_id,
            status=trans.status,
            quantity=trans.quantity,
            borrowed_at=trans.borrowed_at,
            due_date=trans.due_date,
            returned_at=trans.returned_at,
            purpose=trans.purpose,
            notes=trans.notes,
            condition_at_borrow=trans.condition_at_borrow,
            condition_at_return=trans.condition_at_return,
            created_at=trans.created_at,
            updated_at=trans.updated_at,
            user_name=user.full_name if user else "Unknown User",
            user_email=user.email if user else "unknown@email.com",
            item_name=item.name if item else "Unknown Item",
            item_code=item.item_code if item else "UNKNOWN"
        ))

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return TransactionListResponse(
        transactions=detailed_transactions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/my-active", response_model=list[TransactionDetailResponse])
async def get_my_active_borrows(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get current user's active borrows.
    Returns all items currently borrowed by the authenticated user.
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.status == TransactionStatus.BORROWED
    ).order_by(Transaction.borrowed_at.desc()).all()

    detailed_transactions = []
    for trans in transactions:
        item = db.query(Item).filter(Item.id == trans.item_id).first()

        detailed_transactions.append(TransactionDetailResponse(
            id=trans.id,
            user_id=trans.user_id,
            item_id=trans.item_id,
            status=trans.status,
            quantity=trans.quantity,
            borrowed_at=trans.borrowed_at,
            due_date=trans.due_date,
            returned_at=trans.returned_at,
            purpose=trans.purpose,
            notes=trans.notes,
            condition_at_borrow=trans.condition_at_borrow,
            condition_at_return=trans.condition_at_return,
            created_at=trans.created_at,
            updated_at=trans.updated_at,
            user_name=current_user.full_name,
            user_email=current_user.email,
            item_name=item.name if item else "Unknown Item",
            item_code=item.item_code if item else "UNKNOWN"
        ))

    return detailed_transactions


@router.get("/active-for-item/{item_id}", response_model=list[TransactionDetailResponse])
async def get_active_borrows_for_item(
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all active borrows for a specific item.

    Used by the Return workflow after scanning an item QR code:
    - Regular users → only their own active borrow for that item.
    - Admins → all active borrows for that item (needed to return on
      behalf of any user).

    Args:
        item_id: Item ID extracted from the scanned QR code
    """
    query = db.query(Transaction).filter(
        Transaction.item_id == item_id,
        Transaction.status == TransactionStatus.BORROWED
    )

    if not current_user.is_admin:
        query = query.filter(Transaction.user_id == current_user.id)

    transactions = query.order_by(Transaction.borrowed_at.desc()).all()

    detailed = []
    for trans in transactions:
        user = db.query(User).filter(User.id == trans.user_id).first()
        item = db.query(Item).filter(Item.id == trans.item_id).first()
        detailed.append(TransactionDetailResponse(
            id=trans.id,
            user_id=trans.user_id,
            item_id=trans.item_id,
            status=trans.status,
            quantity=trans.quantity,
            borrowed_at=trans.borrowed_at,
            due_date=trans.due_date,
            returned_at=trans.returned_at,
            purpose=trans.purpose,
            notes=trans.notes,
            condition_at_borrow=trans.condition_at_borrow,
            condition_at_return=trans.condition_at_return,
            created_at=trans.created_at,
            updated_at=trans.updated_at,
            user_name=user.full_name if user else "Unknown User",
            user_email=user.email if user else "unknown@email.com",
            item_name=item.name if item else "Unknown Item",
            item_code=item.item_code if item else "UNKNOWN"
        ))

    return detailed


@router.post("/requests/", response_model=RequestDetailResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/requests", response_model=RequestDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
        request_data: RequestCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a new employee request."""
    if request_data.item_id:
        item = db.query(Item).filter(Item.id == request_data.item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with ID {request_data.item_id} not found"
            )

    new_request = Request(
        user_id=current_user.id,
        item_id=request_data.item_id,
        order_type=request_data.order_type,
        # Legacy `request_type` column kept in sync with the real `order_type`
        # enum so older code/filters that still read `request_type` keep working.
        request_type=request_data.order_type.value,
        title=request_data.title,
        description=request_data.description,
        needed_date=request_data.needed_date,
        status="pending"
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    item_name = None
    if new_request.item_id:
        item = db.query(Item).filter(Item.id == new_request.item_id).first()
        item_name = item.name if item else None

    return RequestDetailResponse(
        id=new_request.id,
        user_id=new_request.user_id,
        item_id=new_request.item_id,
        order_type=new_request.order_type,
        request_type=new_request.request_type,
        title=new_request.title,
        description=new_request.description,
        needed_date=new_request.needed_date,
        ready_date=new_request.ready_date,
        priority=new_request.priority,
        status=new_request.status,
        admin_response=new_request.admin_response,
        responded_by_admin_id=new_request.responded_by_admin_id,
        responded_at=new_request.responded_at,
        created_at=new_request.created_at,
        updated_at=new_request.updated_at,
        user_name=current_user.full_name,
        user_email=current_user.email,
        item_name=item_name,
        admin_name=None
    )


@router.get("/requests/", response_model=RequestListResponse, include_in_schema=False)
@router.get("/requests", response_model=RequestListResponse)
async def list_requests(
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        status: str | None = Query(None, pattern="^(pending|approved|rejected|completed)$"),
        priority: str | None = Query(None, pattern="^(low|normal|high|urgent)$"),
        request_type: str | None = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get paginated list of requests."""
    query = db.query(Request)

    if not current_user.is_admin:
        query = query.filter(Request.user_id == current_user.id)

    if status:
        query = query.filter(Request.status == status)
    if priority:
        query = query.filter(Request.priority == priority)
    if request_type:
        query = query.filter(Request.request_type == request_type)

    total = query.count()
    offset = (page - 1) * page_size
    requests = query.order_by(Request.created_at.desc()).offset(offset).limit(page_size).all()

    detailed_requests = []
    for req in requests:
        user = db.query(User).filter(User.id == req.user_id).first()
        item = db.query(Item).filter(Item.id == req.item_id).first() if req.item_id else None
        admin = db.query(User).filter(
            User.id == req.responded_by_admin_id).first() if req.responded_by_admin_id else None

        detailed_requests.append(RequestDetailResponse(
            id=req.id,
            user_id=req.user_id,
            item_id=req.item_id,
            order_type=req.order_type,
            request_type=req.request_type,
            title=req.title,
            description=req.description,
            needed_date=req.needed_date,
            ready_date=req.ready_date,
            priority=req.priority,
            status=req.status,
            admin_response=req.admin_response,
            responded_by_admin_id=req.responded_by_admin_id,
            responded_at=req.responded_at,
            created_at=req.created_at,
            updated_at=req.updated_at,
            user_name=user.full_name if user else "Unknown",
            user_email=user.email if user else "unknown@email.com",
            item_name=item.name if item else None,
            admin_name=admin.full_name if admin else None
        ))

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return RequestListResponse(
        requests=detailed_requests,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/requests/{request_id}", response_model=RequestDetailResponse)
async def get_request(
        request_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a specific request by ID."""
    request = db.query(Request).filter(Request.id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request {request_id} not found"
        )

    if request.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this request"
        )

    user = db.query(User).filter(User.id == request.user_id).first()
    item = db.query(Item).filter(Item.id == request.item_id).first() if request.item_id else None
    admin = db.query(User).filter(
        User.id == request.responded_by_admin_id).first() if request.responded_by_admin_id else None

    return RequestDetailResponse(
        id=request.id,
        user_id=request.user_id,
        item_id=request.item_id,
        order_type=request.order_type,
        request_type=request.request_type,
        title=request.title,
        description=request.description,
        needed_date=request.needed_date,
        ready_date=request.ready_date,
        priority=request.priority,
        status=request.status,
        admin_response=request.admin_response,
        responded_by_admin_id=request.responded_by_admin_id,
        responded_at=request.responded_at,
        created_at=request.created_at,
        updated_at=request.updated_at,
        user_name=user.full_name if user else "Unknown",
        user_email=user.email if user else "unknown@email.com",
        item_name=item.name if item else None,
        admin_name=admin.full_name if admin else None
    )


@router.put("/requests/{request_id}", response_model=RequestDetailResponse)
async def update_request(
        request_id: int,
        request_update: RequestUpdate,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """Update request status and add admin response (Admin only)."""
    request = db.query(Request).filter(Request.id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request {request_id} not found"
        )

    if request_update.status:
        request.status = request_update.status

    if request_update.admin_response:
        request.admin_response = request_update.admin_response

    request.responded_by_admin_id = current_admin.id
    request.responded_at = datetime.now(UTC)

    db.commit()
    db.refresh(request)

    user = db.query(User).filter(User.id == request.user_id).first()
    item = db.query(Item).filter(Item.id == request.item_id).first() if request.item_id else None

    return RequestDetailResponse(
        id=request.id,
        user_id=request.user_id,
        item_id=request.item_id,
        order_type=request.order_type,
        request_type=request.request_type,
        title=request.title,
        description=request.description,
        needed_date=request.needed_date,
        ready_date=request.ready_date,
        priority=request.priority,
        status=request.status,
        admin_response=request.admin_response,
        responded_by_admin_id=request.responded_by_admin_id,
        responded_at=request.responded_at,
        created_at=request.created_at,
        updated_at=request.updated_at,
        user_name=user.full_name if user else "Unknown",
        user_email=user.email if user else "unknown@email.com",
        item_name=item.name if item else None,
        admin_name=current_admin.full_name
    )


@router.delete("/requests/{request_id}")
async def delete_request(
        request_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete a request. Users can delete pending requests. Admins can delete any."""
    request = db.query(Request).filter(Request.id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request {request_id} not found"
        )

    if request.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this request"
        )

    if not current_user.is_admin and request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete pending requests"
        )

    db.delete(request)
    db.commit()

    return {"message": "Request deleted successfully", "request_id": request_id}


@router.get("/{transaction_id}", response_model=TransactionDetailResponse)
async def get_transaction(
        transaction_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a specific transaction by ID."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found"
        )

    if transaction.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this transaction"
        )

    user = db.query(User).filter(User.id == transaction.user_id).first()
    item = db.query(Item).filter(Item.id == transaction.item_id).first()

    return TransactionDetailResponse(
        id=transaction.id,
        user_id=transaction.user_id,
        item_id=transaction.item_id,
        status=transaction.status,
        quantity=transaction.quantity,
        borrowed_at=transaction.borrowed_at,
        due_date=transaction.due_date,
        returned_at=transaction.returned_at,
        purpose=transaction.purpose,
        notes=transaction.notes,
        condition_at_borrow=transaction.condition_at_borrow,
        condition_at_return=transaction.condition_at_return,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        user_name=user.full_name if user else "Unknown",
        user_email=user.email if user else "unknown@email.com",
        item_name=item.name if item else "Unknown",
        item_code=item.item_code if item else "UNKNOWN"
    )
