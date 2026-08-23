import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.qr_generator import qr_generator
from src.core.security import get_current_admin_user, get_current_user, get_password_hash
from src.models.review import Review
from src.models.transaction import Transaction
from src.models.user import User
from src.schemas.user_schema import (
    UserChangePassword,
    UserCreate,
    UserListResponse,
    UserQRCode,
    UserResponse,
    UserStats,
    UserUpdate,
)

router = APIRouter( tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
        user_data: UserCreate,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Create a new user (Admin only).
    Automatically generates QR code for the user.
    """
    # Capacity limits
    total_users = db.query(User).count()
    if total_users >= 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User limit reached (max 500 users)"
        )
    if getattr(user_data, 'is_admin', False):
        total_admins = db.query(User).filter(User.is_admin == True).count()
        if total_admins >= 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin limit reached (max 10 admins)"
            )

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if employee_id already exists
    if user_data.employee_id:
        existing_employee = db.query(User).filter(User.employee_id == user_data.employee_id).first()
        if existing_employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee ID already exists"
            )

    # Create user
    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        department=user_data.department,
        phone=user_data.phone,
        employee_id=user_data.employee_id,
        is_admin=user_data.is_admin,
        qr_code_data="temp"  # Temporary, will be updated after getting ID
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate QR code with actual user ID
    qr_code_data = qr_generator.generate_user_qr_data(new_user.id, new_user.email)
    qr_code_image = qr_generator.generate_qr_code_base64(qr_code_data)

    new_user.qr_code_data = qr_code_data
    new_user.qr_code_image = qr_code_image

    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/", response_model=UserListResponse)
async def list_users(
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        search: str | None = None,
        is_active: bool | None = None,
        is_admin: bool | None = None,
        department: str | None = None,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Get list of users with pagination and filters (Admin only).
    """
    query = db.query(User)

    # Apply filters
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.employee_id.ilike(f"%{search}%"))
        )

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if is_admin is not None:
        query = query.filter(User.is_admin == is_admin)

    if department:
        query = query.filter(User.department == department)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()

    total_pages = math.ceil(total / page_size)

    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile."""
    return current_user


@router.get("/me/qr", response_model=UserQRCode)
async def get_my_qr_code(current_user: User = Depends(get_current_user)):
    """Get current user's QR code."""
    return current_user


@router.get("/me/stats", response_model=UserStats)
async def get_my_stats(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Get current user's statistics."""
    total_borrows = db.query(func.count(Transaction.id)).filter(
        Transaction.user_id == current_user.id
    ).scalar()

    active_borrows = db.query(func.count(Transaction.id)).filter(
        Transaction.user_id == current_user.id,
        Transaction.status == "borrowed"
    ).scalar()

    total_returns = db.query(func.count(Transaction.id)).filter(
        Transaction.user_id == current_user.id,
        Transaction.status == "returned"
    ).scalar()

    overdue_items = db.query(func.count(Transaction.id)).filter(
        Transaction.user_id == current_user.id,
        Transaction.status == "overdue"
    ).scalar()

    total_reviews = db.query(func.count(Review.id)).filter(
        Review.user_id == current_user.id
    ).scalar()

    return {
        "total_borrows": total_borrows or 0,
        "active_borrows": active_borrows or 0,
        "total_returns": total_returns or 0,
        "overdue_items": overdue_items or 0,
        "total_reviews": total_reviews or 0
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """Get user by ID (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
        user_update: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update current user's profile (non-admin fields only)."""
    # Non-admin users can only update certain fields
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.department is not None:
        current_user.department = user_update.department
    if user_update.phone is not None:
        current_user.phone = user_update.phone

    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
        user_id: int,
        user_update: UserUpdate,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """Update user by ID (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update fields — convert empty strings to None for UNIQUE nullable fields
    NULLABLE_UNIQUE = {"employee_id", "phone", "department"}
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value == "" and field in NULLABLE_UNIQUE:
            value = None
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/me/change-password")
async def change_my_password(
        password_data: UserChangePassword,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Change current user's password."""
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "Password updated successfully"}


@router.delete("/{user_id}")
async def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """Delete user by ID (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent deleting yourself
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}