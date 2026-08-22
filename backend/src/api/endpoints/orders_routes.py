"""
ORDERS SECTION — Drop these routes into transactions.py
Place ALL /requests routes BEFORE the /{transaction_id} route to avoid 403.

Required model fields on the Request model (add if missing):
  is_ready    = Column(Boolean, default=False)
  needed_date = Column(DateTime(timezone=True), nullable=True)
  ready_date  = Column(DateTime(timezone=True), nullable=True)
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import get_current_admin_user, get_current_user
from src.models.item import Item
from src.models.transaction import Request
from src.models.user import User
from src.schemas.transaction_schema import (
    RequestCreate,
    RequestDetailResponse,
    RequestListResponse,
    RequestUpdate,
)

router = APIRouter(tags=["Orders"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_response(req: Request, db: Session, admin_name: str | None = None) -> RequestDetailResponse:
    """Build a full RequestDetailResponse from a Request ORM object."""
    user = db.query(User).filter(User.id == req.user_id).first()
    item = db.query(Item).filter(Item.id == req.item_id).first() if req.item_id else None
    return RequestDetailResponse(
        id=req.id,
        user_id=req.user_id,
        request_type=req.request_type,
        title=req.title,
        description=req.description,
        item_id=req.item_id,
        needed_date=getattr(req, "needed_date", None),
        ready_date=getattr(req, "ready_date", None),
        status=req.status,
        is_ready=getattr(req, "is_ready", False),
        admin_response=req.admin_response,
        admin_name=admin_name,
        created_at=req.created_at,
        updated_at=req.updated_at,
        user_name=user.full_name if user else "Unknown",
        user_email=user.email if user else "",
        user_employee_id=getattr(user, "employee_id", None) if user else None,
        item_name=item.name if item else None,
    )


def _get_or_404(db: Session, request_id: int) -> Request:
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail=f"Order {request_id} not found")
    return req


# ── User endpoints ────────────────────────────────────────────────────────────

@router.post(
    "/requests",
    response_model=RequestDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order (user)",
)
@router.post("/requests/", response_model=RequestDetailResponse,
             status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_request(
    request_data: RequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Any authenticated user can create an order.
    order_type: new_item | special_borrow | other
    item_id and needed_date are optional.
    """
    # Validate item exists if provided
    if request_data.item_id:
        item = db.query(Item).filter(Item.id == request_data.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {request_data.item_id} not found")

    new_request = Request(
        user_id=current_user.id,
        request_type=request_data.request_type,
        title=request_data.title,
        description=request_data.description,
        item_id=request_data.item_id,
        status="pending",
        is_ready=False,
    )

    # Set optional fields only if the column exists on the model
    if hasattr(new_request, "needed_date"):
        new_request.needed_date = request_data.needed_date
    if hasattr(new_request, "priority"):
        new_request.priority = "normal"

    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return _build_response(new_request, db)


@router.get(
    "/requests/me",
    response_model=RequestListResponse,
    summary="Get my own orders (user)",
)
async def list_my_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns only the calling user's own orders.
    Users NEVER see other users' orders.
    """
    q = db.query(Request).filter(Request.user_id == current_user.id)

    if status_filter:
        q = q.filter(Request.status == status_filter.lower())

    total = q.count()
    requests = (
        q.order_by(Request.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return RequestListResponse(
        requests=[_build_response(r, db) for r in requests],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.patch(
    "/requests/{request_id}/cancel",
    response_model=RequestDetailResponse,
    summary="Cancel own pending order (user)",
)
async def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    User can cancel ONLY their own order AND only if still pending.
    """
    req = _get_or_404(db, request_id)

    # Security: user can only cancel their own
    if req.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if req.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order with status '{req.status}'. Only pending orders can be cancelled."
        )

    req.status = "rejected"  # reuse rejected as cancelled state
    db.commit()
    db.refresh(req)
    return _build_response(req, db)


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get(
    "/requests",
    response_model=RequestListResponse,
    summary="List all orders (admin)",
)
@router.get("/requests/", response_model=RequestListResponse, include_in_schema=False)
async def list_all_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status",
                                          description="pending|approved|rejected|ready"),
    request_type: str | None = Query(None),
    user_id: int | None = Query(None, description="Filter by specific user"),
    search: str | None = Query(None, description="Search by user name or order title"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # admin check below
):
    """
    Admin sees ALL orders. Regular users are redirected to /requests/me.
    Supports filtering by status, type, user_id, and text search.
    """
    # Non-admins can only see their own
    if not current_user.is_admin:
        q = db.query(Request).filter(Request.user_id == current_user.id)
    else:
        q = db.query(Request)

    if status_filter:
        q = q.filter(Request.status == status_filter.lower())
    if request_type:
        q = q.filter(Request.request_type == request_type.lower())
    if user_id and current_user.is_admin:
        q = q.filter(Request.user_id == user_id)
    if search and current_user.is_admin:
        q = q.join(User, User.id == Request.user_id).filter(
            User.full_name.ilike(f"%{search}%") |
            Request.title.ilike(f"%{search}%")
        )

    total = q.count()
    requests = (
        q.order_by(Request.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return RequestListResponse(
        requests=[_build_response(r, db) for r in requests],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.get(
    "/requests/{request_id}",
    response_model=RequestDetailResponse,
    summary="Get single order details",
)
async def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = _get_or_404(db, request_id)

    # Users can only see their own
    if not current_user.is_admin and req.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    return _build_response(req, db)


@router.put(
    "/requests/{request_id}",
    response_model=RequestDetailResponse,
    summary="Update order status and admin notes (admin only)",
)
async def update_request(
    request_id: int,
    update: RequestUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Admin can update:
    - status: pending | approved | rejected | ready
    - is_ready: boolean flag
    - admin_response: message to user
    - ready_date: actual ready date
    Setting status='ready' automatically sets is_ready=True.
    """
    req = _get_or_404(db, request_id)

    if update.status is not None:
        req.status = update.status
        # Auto-set is_ready when status = ready
        if update.status == "ready":
            req.is_ready = True

    if update.is_ready is not None:
        req.is_ready = update.is_ready
        if update.is_ready and req.status not in ("ready", "completed"):
            req.status = "ready"

    if update.admin_response is not None:
        req.admin_response = update.admin_response

    if update.ready_date is not None and hasattr(req, "ready_date"):
        req.ready_date = update.ready_date

    req.responded_by_admin_id = current_admin.id
    req.responded_at = datetime.now(UTC)

    db.commit()
    db.refresh(req)
    return _build_response(req, db, admin_name=current_admin.full_name)


@router.delete(
    "/requests/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete order (admin only)",
)
async def delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Hard delete. Admin only."""
    req = _get_or_404(db, request_id)
    db.delete(req)
    db.commit()

