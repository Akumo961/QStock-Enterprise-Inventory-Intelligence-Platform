import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.qr_generator import qr_generator
from src.core.security import get_current_admin_user, get_current_user
from src.models.item import Item, ItemCategory, ItemStatus
from src.models.review import Review
from src.models.transaction import Transaction
from src.models.user import User
from src.schemas.item_schema import (
    ItemAvailability,
    ItemCreate,
    ItemListResponse,
    ItemQRCode,
    ItemResponse,
    ItemStats,
    ItemUpdate,
)

router = APIRouter( tags=["Items"])


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
        item_data: ItemCreate,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Create a new inventory item (Admin only).
    Automatically generates unique item code and QR code.
    """
    # Generate unique item code if not provided
    if not item_data.item_code:
        item_code = f"ITEM-{uuid.uuid4().hex[:8].upper()}"
    else:
        item_code = item_data.item_code

    # Check if item code already exists
    existing_item = db.query(Item).filter(Item.item_code == item_code).first()
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item code already exists"
        )

    # Capacity limits
    total_items = db.query(Item).count()
    if total_items >= 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item limit reached (max 1000 items)"
        )

    # How many of the total quantity are available right now. Defaults to
    # the full quantity (everything is available on creation) unless the
    # admin specifies otherwise — but can never exceed quantity.
    available_quantity = (
        item_data.available_quantity
        if item_data.available_quantity is not None
        else item_data.quantity
    )
    if available_quantity > item_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"available_quantity ({available_quantity}) cannot exceed "
                f"quantity ({item_data.quantity})."
            ),
        )

    # Count admins if creating an admin item (not applicable here, handled in users)

    # FIX: Convert empty strings to None for UNIQUE-constrained nullable fields.
    # serial_number has a UNIQUE constraint — storing '' for multiple items
    # causes UniqueViolation. NULL is exempt from uniqueness checks.
    def empty_to_none(val):
        return None if val == '' else val

    # Create item
    new_item = Item(
        name=item_data.name,
        description=empty_to_none(item_data.description),
        item_code=item_code,
        category=item_data.category,
        serial_number=empty_to_none(item_data.serial_number),
        brand=empty_to_none(item_data.brand),
        model=empty_to_none(item_data.model),
        purchase_date=item_data.purchase_date,
        location=empty_to_none(item_data.location),
        quantity=item_data.quantity,
        available_quantity=available_quantity,
        is_borrowable=item_data.is_borrowable,
        requires_approval=item_data.requires_approval,
        max_borrow_days=item_data.max_borrow_days,
        notes=empty_to_none(item_data.notes),
        image_url=empty_to_none(item_data.image_url),
        qr_code_data="temp"  # Temporary
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    # Generate QR code with actual item ID
    qr_code_data = qr_generator.generate_item_qr_data(new_item.id, new_item.item_code)
    qr_code_image = qr_generator.generate_qr_code_base64(qr_code_data)

    new_item.qr_code_data = qr_code_data
    new_item.qr_code_image = qr_code_image

    db.commit()
    db.refresh(new_item)

    return new_item


@router.get("/", response_model=ItemListResponse)
async def list_items(
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        search: str | None = None,
        category: ItemCategory | None = None,
        status: ItemStatus | None = None,
        is_borrowable: bool | None = None,
        available_only: bool = False,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get list of items with pagination and filters.
    """
    query = db.query(Item)

    # Apply filters
    if search:
        query = query.filter(
            (Item.name.ilike(f"%{search}%")) |
            (Item.item_code.ilike(f"%{search}%")) |
            (Item.description.ilike(f"%{search}%")) |
            (Item.brand.ilike(f"%{search}%"))
        )

    if category:
        query = query.filter(Item.category == category)

    if status:
        query = query.filter(Item.status == status)

    if is_borrowable is not None:
        query = query.filter(Item.is_borrowable == is_borrowable)

    if available_only:
        query = query.filter(
            Item.status == ItemStatus.AVAILABLE,
            Item.is_borrowable == True,
            Item.available_quantity > 0
        )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    total_pages = math.ceil(total / page_size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get item by ID."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    return item


@router.get("/{item_id}/qr", response_model=ItemQRCode)
async def get_item_qr_code(
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get item's QR code."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    return item


@router.get("/{item_id}/stats", response_model=ItemStats)
async def get_item_stats(
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get item statistics."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    total_borrows = db.query(func.count(Transaction.id)).filter(
        Transaction.item_id == item_id
    ).scalar()

    current_borrowed = db.query(func.count(Transaction.id)).filter(
        Transaction.item_id == item_id,
        Transaction.status == "borrowed"
    ).scalar()

    total_returns = db.query(func.count(Transaction.id)).filter(
        Transaction.item_id == item_id,
        Transaction.status == "returned"
    ).scalar()

    avg_rating = db.query(func.avg(Review.rating)).filter(
        Review.item_id == item_id,
        Review.rating.isnot(None)
    ).scalar()

    total_reviews = db.query(func.count(Review.id)).filter(
        Review.item_id == item_id
    ).scalar()

    times_reported = db.query(func.count(Review.id)).filter(
        Review.item_id == item_id,
        Review.has_issue == True
    ).scalar()

    return {
        "total_borrows": total_borrows or 0,
        "current_borrowed": current_borrowed or 0,
        "total_returns": total_returns or 0,
        "average_rating": float(avg_rating) if avg_rating else None,
        "total_reviews": total_reviews or 0,
        "times_reported": times_reported or 0
    }


@router.get("/{item_id}/availability", response_model=ItemAvailability)
async def check_item_availability(
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Check if item is available for borrowing."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    is_available = (
            item.status == ItemStatus.AVAILABLE and
            item.is_borrowable and
            item.available_quantity > 0
    )

    return {
        "item_id": item.id,
        "is_available": is_available,
        "available_quantity": item.available_quantity,
        "total_quantity": item.quantity,
        "status": item.status,
        "next_available_date": None  # Could be calculated from due dates
    }


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
        item_id: int,
        item_update: ItemUpdate,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """Update item by ID (Admin only)."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    # Update fields
    # FIX: Convert empty strings to None for UNIQUE-constrained nullable fields
    NULLABLE_UNIQUE = {'serial_number', 'brand', 'model', 'location', 'description', 'notes', 'image_url'}
    update_data = item_update.model_dump(exclude_unset=True)

    # Admin can change quantity / available_quantity freely, at any moment.
    # Rather than ever blocking the request, the system keeps the numbers
    # sane automatically: available_quantity is clamped into [0, quantity].
    currently_borrowed = item.quantity - item.available_quantity
    new_quantity = update_data.get('quantity', item.quantity)
    new_available_quantity = update_data.get('available_quantity', item.available_quantity)

    if 'quantity' in update_data and 'available_quantity' not in update_data:
        # Quantity changed but available_quantity wasn't explicitly set —
        # keep the same number of items "currently borrowed" consistent,
        # clamping at 0 instead of rejecting the update.
        new_available_quantity = max(0, new_quantity - currently_borrowed)
        update_data['available_quantity'] = new_available_quantity

    # Clamp into a sane range instead of erroring — the admin always has
    # final say over their own inventory numbers.
    new_available_quantity = max(0, min(new_available_quantity, new_quantity))
    update_data['available_quantity'] = new_available_quantity

    for field, value in update_data.items():
        if value == '' and field in NULLABLE_UNIQUE:
            value = None
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
async def delete_item(
        item_id: int,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """Delete item by ID (Admin only)."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    # Check if item has active borrows
    active_borrows = db.query(Transaction).filter(
        Transaction.item_id == item_id,
        Transaction.status == "borrowed"
    ).count()

    if active_borrows > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete item with active borrows"
        )

    db.delete(item)
    db.commit()

    return {"message": "Item deleted successfully"}


@router.post("/{item_id}/regenerate-qr", response_model=ItemQRCode)
async def regenerate_item_qr_code(
        item_id: int,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """Regenerate QR code for an item (Admin only)."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    # Generate new QR code
    qr_code_data = qr_generator.generate_item_qr_data(item.id, item.item_code)
    qr_code_image = qr_generator.generate_qr_code_base64(qr_code_data)

    item.qr_code_data = qr_code_data
    item.qr_code_image = qr_code_image

    db.commit()
    db.refresh(item)

    return item