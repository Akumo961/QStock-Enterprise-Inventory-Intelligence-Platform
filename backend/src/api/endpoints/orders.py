"""
orders.py

Orders API

Routes:
    POST   /api/orders
    GET    /api/orders/me
    GET    /api/orders
    GET    /api/orders/{order_id}
    PUT    /api/orders/{order_id}
    PATCH  /api/orders/{order_id}/cancel
    DELETE /api/orders/{order_id}

Order Types:
    new_item
    special_borrow
    other

Order Statuses:
    pending
    approved
    rejected
    ready
"""

from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import (
    get_current_admin_user,
    get_current_user,
)
from src.models.item import Item
from src.models.transaction import (
    Order,
    OrderStatus,
    OrderType,
)
from src.models.user import User
from src.schemas.transaction_schema import (
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    OrderUpdate,
)

router = APIRouter(tags=["Orders"])


# ============================================================================
# Helpers
# ============================================================================

def _default_title(order_type: OrderType) -> str:
    mapping = {
        OrderType.NEW_ITEM: "New Item Request",
        OrderType.SPECIAL_BORROW: "Special Borrow Request",
        OrderType.OTHER: "Other Request",
    }
    return mapping.get(order_type, "Request")


def _build_response(order: Order, db: Session) -> OrderResponse:
    user = (
        db.query(User)
        .filter(User.id == order.user_id)
        .first()
    )

    item = (
        db.query(Item)
        .filter(Item.id == order.item_id)
        .first()
        if order.item_id
        else None
    )

    admin = (
        db.query(User)
        .filter(User.id == order.responded_by_admin_id)
        .first()
        if order.responded_by_admin_id
        else None
    )

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        order_type=order.order_type,
        title=order.title,
        description=order.description,
        item_id=order.item_id,
        needed_date=order.needed_date,
        ready_date=order.ready_date,
        status=order.status,
        admin_response=order.admin_response,
        responded_by_admin_id=order.responded_by_admin_id,
        responded_at=order.responded_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        user_name=user.full_name if user else "",
        user_email=user.email if user else "",
        user_employee_id=getattr(user, "employee_id", None)
        if user
        else None,
        item_name=item.name if item else None,
        admin_name=admin.full_name if admin else None,
    )


def _get_or_404(db: Session, order_id: int) -> Order:
    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail=f"Order {order_id} not found",
        )

    return order


# ============================================================================
# User Endpoints
# ============================================================================

@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.item_id:
        item = (
            db.query(Item)
            .filter(Item.id == data.item_id)
            .first()
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Item {data.item_id} not found",
            )

    title = data.title or _default_title(data.order_type)

    order = Order(
        user_id=current_user.id,
        order_type=data.order_type,
        request_type=data.order_type.value,
        title=title,
        description=data.description,
        item_id=data.item_id,
        needed_date=data.needed_date,
        status=OrderStatus.PENDING,
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return _build_response(order, db)


@router.get("/me", response_model=OrderListResponse)
async def list_my_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: OrderStatus | None = Query(
        None,
        alias="status",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Order).filter(
        Order.user_id == current_user.id
    )

    if status_filter:
        query = query.filter(
            Order.status == status_filter
        )

    total = query.count()

    orders = (
        query.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return OrderListResponse(
        orders=[_build_response(o, db) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.patch(
    "/{order_id}/cancel",
    response_model=OrderResponse,
)
async def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = _get_or_404(db, order_id)

    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not your order",
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Only pending orders can be cancelled",
        )

    order.status = OrderStatus.REJECTED

    db.commit()
    db.refresh(order)

    return _build_response(order, db)


# ============================================================================
# Shared / Admin Endpoints
# ============================================================================

@router.get("", response_model=OrderListResponse)
@router.get(
    "/",
    response_model=OrderListResponse,
    include_in_schema=False,
)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: OrderStatus | None = Query(
        None,
        alias="status",
    ),
    order_type: OrderType | None = Query(None),
    user_id: int | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.is_admin:
        query = db.query(Order)

        if user_id:
            query = query.filter(
                Order.user_id == user_id
            )
    else:
        query = db.query(Order).filter(
            Order.user_id == current_user.id
        )

    if status_filter:
        query = query.filter(
            Order.status == status_filter
        )

    if order_type:
        query = query.filter(
            Order.order_type == order_type
        )

    if search:
        query = (
            query.join(User, User.id == Order.user_id)
            .filter(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    Order.description.ilike(f"%{search}%"),
                    Order.title.ilike(f"%{search}%"),
                )
            )
        )

    total = query.count()

    orders = (
        query.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return OrderListResponse(
        orders=[_build_response(o, db) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
async def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = _get_or_404(db, order_id)

    if (
        not current_user.is_admin
        and order.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Not your order",
        )

    return _build_response(order, db)


@router.put(
    "/{order_id}",
    response_model=OrderResponse,
)
async def update_order(
    order_id: int,
    data: OrderUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        get_current_admin_user
    ),
):
    order = _get_or_404(db, order_id)

    if data.status is not None:
        order.status = data.status

    if data.admin_response is not None:
        order.admin_response = data.admin_response

    if data.ready_date is not None:
        order.ready_date = data.ready_date

    order.responded_by_admin_id = current_admin.id
    order.responded_at = datetime.now(UTC)

    db.commit()
    db.refresh(order)

    return _build_response(order, db)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        get_current_admin_user
    ),
):
    order = _get_or_404(db, order_id)

    db.delete(order)
    db.commit()

