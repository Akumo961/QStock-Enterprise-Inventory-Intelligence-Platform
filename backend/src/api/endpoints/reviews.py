"""
API endpoints for managing reviews/feedback for borrowed items.
Employees can submit reviews after returning items.
"""

import math
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import get_current_admin_user, get_current_user
from src.models.item import Item
from src.models.review import Review
from src.models.transaction import Transaction, TransactionStatus
from src.models.user import User
from src.schemas.review_schema import (
    ReviewCreate,
    ReviewDetailResponse,
    ReviewListResponse,
    ReviewUpdate,
)

router = APIRouter(
    tags=["Reviews"],
    responses={404: {"description": "Review not found"}},
)


def _to_detail(review: Review, db: Session) -> ReviewDetailResponse:
    """Enrich a Review ORM object with user/item display fields."""
    user = db.query(User).filter(User.id == review.user_id).first()
    item = db.query(Item).filter(Item.id == review.item_id).first()
    return ReviewDetailResponse(
        id=review.id,
        user_id=review.user_id,
        item_id=review.item_id,
        transaction_id=review.transaction_id,
        rating=review.rating,
        comment=review.comment,
        has_issue=review.has_issue,
        issue_type=review.issue_type,
        issue_description=review.issue_description,
        issue_severity=review.issue_severity,
        admin_notified=review.admin_notified,
        admin_response=review.admin_response,
        issue_resolved=review.issue_resolved,
        created_at=review.created_at,
        updated_at=review.updated_at,
        user_name=user.full_name if user else "Unknown",
        user_email=user.email if user else "unknown@email.com",
        item_name=item.name if item else "Unknown",
        item_code=item.item_code if item else "",
    )


# ========= ENDPOINTS =========

@router.post("/", response_model=ReviewDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
        review: ReviewCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Create a new review for an item, optionally tied to a specific transaction.

    - **item_id**: ID of the item being reviewed
    - **transaction_id**: Optional ID of the completed (returned) transaction
    - **rating**: 1-5 rating (optional)
    - **comment**: Optional text feedback
    - **has_issue / issue_type / issue_description / issue_severity**: Optional issue report
    """
    item = db.query(Item).filter(Item.id == review.item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    if review.transaction_id:
        transaction = db.query(Transaction).filter(
            Transaction.id == review.transaction_id
        ).first()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found",
            )

        # Only the borrower (or an admin) may review their own transaction
        if transaction.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only review your own transactions",
            )

        if transaction.item_id != review.item_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction does not match the specified item",
            )

        # Item must actually have been returned before it can be reviewed
        if transaction.status != TransactionStatus.RETURNED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot review an item that hasn't been returned yet",
            )

        existing_review = db.query(Review).filter(
            Review.transaction_id == review.transaction_id
        ).first()
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A review already exists for this transaction",
            )

    db_review = Review(
        user_id=current_user.id,
        item_id=review.item_id,
        transaction_id=review.transaction_id,
        rating=review.rating,
        comment=review.comment,
        has_issue=review.has_issue,
        issue_type=review.issue_type,
        issue_description=review.issue_description,
        issue_severity=review.issue_severity,
        admin_notified=review.has_issue,  # flag for admin attention when an issue is reported
    )

    try:
        db.add(db_review)
        db.commit()
        db.refresh(db_review)
        return _to_detail(db_review, db)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating review",
        ) from e


@router.get("/", response_model=ReviewListResponse)
async def get_all_reviews(
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        item_id: int | None = Query(None, description="Filter by item ID"),
        user_id: int | None = Query(None, description="Filter by user ID"),
        min_rating: int | None = Query(None, ge=1, le=5, description="Minimum rating"),
        has_issue: bool | None = Query(None, description="Filter by issue-reported reviews"),
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user),
):
    """Get all reviews with optional filters (admin only)."""
    query = db.query(Review)

    if item_id:
        query = query.filter(Review.item_id == item_id)
    if user_id:
        query = query.filter(Review.user_id == user_id)
    if min_rating:
        query = query.filter(Review.rating >= min_rating)
    if has_issue is not None:
        query = query.filter(Review.has_issue == has_issue)

    total = query.count()
    offset = (page - 1) * page_size
    reviews = query.order_by(desc(Review.created_at)).offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return ReviewListResponse(
        reviews=[_to_detail(r, db) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/summary")
async def get_review_summary(
        days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user),
):
    """Get summary statistics for reviews (admin only)."""
    since_date = datetime.now(UTC) - timedelta(days=days)
    reviews_query = db.query(Review).filter(Review.created_at >= since_date)
    reviews = reviews_query.all()
    total_reviews = len(reviews)

    if total_reviews == 0:
        return {
            "total_reviews": 0,
            "average_rating": 0.0,
            "rating_distribution": {},
            "issue_count": 0,
            "recent_reviews": [],
        }

    rated = [r.rating for r in reviews if r.rating is not None]
    average_rating = round(sum(rated) / len(rated), 2) if rated else 0.0

    rating_distribution = {}
    for i in range(1, 6):
        count = sum(1 for r in reviews if r.rating == i)
        if count > 0:
            rating_distribution[str(i)] = count

    issue_count = sum(1 for r in reviews if r.has_issue)

    recent = sorted(reviews, key=lambda r: r.created_at, reverse=True)[:10]

    return {
        "total_reviews": total_reviews,
        "average_rating": average_rating,
        "rating_distribution": rating_distribution,
        "issue_count": issue_count,
        "recent_reviews": [_to_detail(r, db) for r in recent],
    }


@router.get("/item/{item_id}", response_model=ReviewListResponse)
async def get_reviews_by_item(
        item_id: int,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        db: Session = Depends(get_db),
):
    """Get all reviews for a specific item (public — anyone can see item reviews)."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    query = db.query(Review).filter(Review.item_id == item_id)
    total = query.count()
    offset = (page - 1) * page_size
    reviews = query.order_by(desc(Review.created_at)).offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return ReviewListResponse(
        reviews=[_to_detail(r, db) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/user/{user_id}", response_model=ReviewListResponse)
async def get_reviews_by_user(
        user_id: int,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Get all reviews submitted by a specific user (self or admin only)."""
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view another user's reviews",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    query = db.query(Review).filter(Review.user_id == user_id)
    total = query.count()
    offset = (page - 1) * page_size
    reviews = query.order_by(desc(Review.created_at)).offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return ReviewListResponse(
        reviews=[_to_detail(r, db) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/transaction/{transaction_id}", response_model=ReviewDetailResponse)
async def get_review_by_transaction(
        transaction_id: int,
        db: Session = Depends(get_db),
):
    """Get the review associated with a specific transaction."""
    review = db.query(Review).filter(Review.transaction_id == transaction_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No review found for this transaction",
        )
    return _to_detail(review, db)


@router.get("/stats/item/{item_id}")
async def get_item_review_stats(
        item_id: int,
        db: Session = Depends(get_db),
):
    """Get review statistics for a specific item."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    reviews = db.query(Review).filter(Review.item_id == item_id).all()

    if not reviews:
        return {
            "item_id": item_id,
            "item_name": item.name,
            "total_reviews": 0,
            "average_rating": None,
            "issue_count": 0,
        }

    rated = [r.rating for r in reviews if r.rating is not None]
    average_rating = round(sum(rated) / len(rated), 2) if rated else None
    issue_count = sum(1 for r in reviews if r.has_issue)

    return {
        "item_id": item_id,
        "item_name": item.name,
        "total_reviews": len(reviews),
        "average_rating": average_rating,
        "issue_count": issue_count,
    }


# NOTE: parametrized "/{review_id}" routes are declared LAST so they don't
# shadow the more specific "/summary", "/item/{id}", "/user/{id}", etc. routes above.

@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review_by_id(
        review_id: int,
        db: Session = Depends(get_db),
):
    """Get a specific review by ID."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    return _to_detail(review, db)


@router.put("/{review_id}", response_model=ReviewDetailResponse)
async def update_review(
        review_id: int,
        review_update: ReviewUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Update an existing review.

    - The review's author may update rating/comment.
    - Only admins may set admin_response / issue_resolved.
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    update_data = review_update.model_dump(exclude_unset=True)

    if not current_user.is_admin:
        if review.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this review",
            )
        # Regular users can't set admin-only fields
        update_data.pop("admin_response", None)
        update_data.pop("issue_resolved", None)

    for field, value in update_data.items():
        setattr(review, field, value)

    try:
        db.commit()
        db.refresh(review)
        return _to_detail(review, db)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating review",
        ) from e


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
        review_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Delete a review. The author or an admin may delete it."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    if review.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this review",
        )

    try:
        db.delete(review)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting review",
        ) from e

