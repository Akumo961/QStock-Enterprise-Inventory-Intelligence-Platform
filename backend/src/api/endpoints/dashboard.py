"""
Dashboard and Analytics API Endpoints
Provides statistics, trends, and insights for administrators
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import get_current_admin_user, get_current_user
from src.models.item import Item, ItemCategory, ItemStatus
from src.models.review import Review
from src.models.transaction import Request, Transaction, TransactionStatus
from src.models.user import User
from src.schemas.dashboard_schema import (
    BorrowingTrend,
    CategoryDistribution,
    DashboardOverview,
    DashboardStats,
    ItemUtilization,
    PopularItemsStats,
    RecentActivity,
    UserActivity,
)

router = APIRouter( tags=["Dashboard"])


# ============================================================================
# OVERVIEW STATISTICS
# ============================================================================

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive dashboard statistics.

    Provides high-level metrics including:
    - User counts (total, active)
    - Item counts by status
    - Transaction statistics
    - Review and request counts

    Args:
        db: Database session
        current_admin: Authenticated admin user

    Returns:
        Dashboard statistics object
    """
    # User statistics
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(
        User.is_active == True
    ).scalar() or 0

    # Item statistics
    total_items = db.query(func.count(Item.id)).scalar() or 0
    available_items = db.query(func.count(Item.id)).filter(
        Item.status == ItemStatus.AVAILABLE,
        Item.is_borrowable == True
    ).scalar() or 0
    borrowed_items = db.query(func.count(Item.id)).filter(
        Item.status == ItemStatus.BORROWED
    ).scalar() or 0
    maintenance_items = db.query(func.count(Item.id)).filter(
        Item.status == ItemStatus.MAINTENANCE
    ).scalar() or 0

    # Transaction statistics
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    active_borrows = db.query(func.count(Transaction.id)).filter(
        Transaction.status == TransactionStatus.BORROWED
    ).scalar() or 0

    # Overdue borrows (borrowed items past due date)
    current_time = datetime.now(UTC)
    overdue_borrows = db.query(func.count(Transaction.id)).filter(
        Transaction.status == TransactionStatus.BORROWED,
        Transaction.due_date < current_time
    ).scalar() or 0

    total_returns = db.query(func.count(Transaction.id)).filter(
        Transaction.status == TransactionStatus.RETURNED
    ).scalar() or 0

    # Review and request statistics
    total_reviews = db.query(func.count(Review.id)).scalar() or 0
    pending_requests = db.query(func.count(Request.id)).filter(
        Request.status == "pending"
    ).scalar() or 0

    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        total_items=total_items,
        available_items=available_items,
        borrowed_items=borrowed_items,
        maintenance_items=maintenance_items,
        total_transactions=total_transactions,
        active_borrows=active_borrows,
        overdue_borrows=overdue_borrows,
        total_returns=total_returns,
        total_reviews=total_reviews,
        pending_requests=pending_requests
    )


# ============================================================================
# POPULAR ITEMS ANALYTICS
# ============================================================================

@router.get("/popular-items", response_model=list[PopularItemsStats])
async def get_popular_items(
        limit: int = Query(10, ge=1, le=50, description="Number of items to return"),
        days: int | None = Query(None, ge=1, description="Filter by last N days"),
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Get most popular items by borrow count.

    Shows which items are borrowed most frequently, helping identify:
    - High-demand items that may need more copies
    - Popular equipment categories
    - Items that should always be in stock

    Args:
        limit: Maximum number of items to return
        days: Optional filter for recent borrows only
        db: Database session
        current_admin: Authenticated admin user

    Returns:
        List of popular items with borrow counts and ratings
    """
    query = db.query(
        Item.id,
        Item.name,
        Item.item_code,
        Item.category,
        func.count(Transaction.id).label('borrow_count'),
        func.avg(Review.rating).label('avg_rating')
    ).join(
        Transaction, Transaction.item_id == Item.id
    ).outerjoin(
        Review, Review.item_id == Item.id
    )

    # Filter by date range if specified
    if days:
        date_threshold = datetime.now(UTC) - timedelta(days=days)
        query = query.filter(Transaction.borrowed_at >= date_threshold)

    # Group and order
    popular_items = query.group_by(
        Item.id, Item.name, Item.item_code, Item.category
    ).order_by(
        desc('borrow_count')
    ).limit(limit).all()

    return [
        PopularItemsStats(
            item_id=item.id,
            item_name=item.name,
            item_code=item.item_code,
            category=item.category.value,
            borrow_count=item.borrow_count,
            average_rating=float(item.avg_rating) if item.avg_rating else None
        )
        for item in popular_items
    ]


# ============================================================================
# ACTIVITY TRACKING
# ============================================================================

@router.get("/recent-activities", response_model=list[RecentActivity])
async def get_recent_activities(
        limit: int = Query(20, ge=1, le=100, description="Number of activities to return"),
        activity_types: list[str] | None = Query(
            None,
            description="Filter by activity types: borrow, return, review, request"
        ),
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Get recent system activities for the activity feed.

    Provides a real-time view of system usage including:
    - Recent borrows and returns
    - New reviews submitted
    - Employee requests

    Args:
        limit: Number of activities to return
        activity_types: Filter by specific activity types
        db: Database session
        current_admin: Authenticated admin user

    Returns:
        List of recent activities with timestamps
    """
    activities = []

    # Fetch recent transactions (borrows and returns)
    if not activity_types or 'borrow' in activity_types or 'return' in activity_types:
        recent_transactions = db.query(Transaction).order_by(
            Transaction.created_at.desc()
        ).limit(limit).all()

        for trans in recent_transactions:
            user = db.query(User).filter(User.id == trans.user_id).first()
            item = db.query(Item).filter(Item.id == trans.item_id).first()

            if (
                    trans.status == TransactionStatus.BORROWED
                    and (not activity_types or "borrow" in activity_types)
            ):
                activities.append(RecentActivity(
                    activity_type="borrow",
                    description=f"borrowed {item.name if item else 'an item'}",
                    user_name=user.full_name if user else "Unknown User",
                    item_name=item.name if item else None,
                    timestamp=trans.borrowed_at
                ))

            elif (
                    trans.status == TransactionStatus.RETURNED
                    and (not activity_types or "return" in activity_types)
            ):
                activities.append(RecentActivity(
                    activity_type="return",
                    description=f"returned {item.name if item else 'an item'}",
                    user_name=user.full_name if user else "Unknown User",
                    item_name=item.name if item else None,
                    timestamp=trans.returned_at or trans.created_at
                ))


    # Fetch recent reviews
    if not activity_types or 'review' in activity_types:
        recent_reviews = db.query(Review).order_by(
            Review.created_at.desc()
        ).limit(limit // 2).all()

        for review in recent_reviews:
            user = db.query(User).filter(User.id == review.user_id).first()
            item = db.query(Item).filter(Item.id == review.item_id).first()

            if review.has_issue:
                description = f"reported an issue with {item.name if item else 'an item'}"
            else:
                description = f"reviewed {item.name if item else 'an item'}"

            activities.append(RecentActivity(
                activity_type="review",
                description=description,
                user_name=user.full_name if user else "Unknown User",
                item_name=item.name if item else None,
                timestamp=review.created_at
            ))

    # Fetch recent requests
    if not activity_types or 'request' in activity_types:
        recent_requests = db.query(Request).order_by(
            Request.created_at.desc()
        ).limit(limit // 2).all()

        for req in recent_requests:
            user = db.query(User).filter(User.id == req.user_id).first()

            activities.append(RecentActivity(
                activity_type="request",
                description=f"submitted request: {req.title}",
                user_name=user.full_name if user else "Unknown User",
                item_name=None,
                timestamp=req.created_at
            ))

    # Sort all activities by timestamp and limit
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    return activities[:limit]


# ============================================================================
# TREND ANALYSIS
# ============================================================================

@router.get("/borrowing-trends", response_model=list[BorrowingTrend])
async def get_borrowing_trends(
        days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Get borrowing and return trends over time.

    Analyzes usage patterns to identify:
    - Peak borrowing periods
    - Return rates
    - Usage trends over time

    Args:
        days: Number of days to analyze (7-365)
        db: Database session
        current_admin: Authenticated admin user

    Returns:
        Daily borrow and return counts for the period
    """
    start_date = datetime.now(UTC) - timedelta(days=days)
    trends = []

    for i in range(days):
        date = start_date + timedelta(days=i)
        next_date = date + timedelta(days=1)

        # Count borrows for this day
        borrow_count = db.query(func.count(Transaction.id)).filter(
            Transaction.borrowed_at >= date,
            Transaction.borrowed_at < next_date
        ).scalar() or 0

        # Count returns for this day
        return_count = db.query(func.count(Transaction.id)).filter(
            Transaction.returned_at >= date,
            Transaction.returned_at < next_date,
            Transaction.status == TransactionStatus.RETURNED
        ).scalar() or 0

        trends.append(BorrowingTrend(
            date=date.strftime('%Y-%m-%d'),
            borrow_count=borrow_count,
            return_count=return_count
        ))

    return trends


# ============================================================================
# CATEGORY ANALYTICS
# ============================================================================

@router.get("/category-distribution", response_model=list[CategoryDistribution])
async def get_category_distribution(
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Get item distribution across categories.

    Shows inventory composition by category, helping to identify:
    - Over-represented categories
    - Under-stocked categories
    - Resource allocation needs

    Args:
        db: Database session
        current_admin: Authenticated admin user

    Returns:
        List of categories with counts and percentages
    """
    # Get total item count
    total_items = db.query(func.count(Item.id)).scalar() or 1  # Avoid division by zero

    # Get counts by category
    categories = db.query(
        Item.category,
        func.count(Item.id).label('count')
    ).group_by(Item.category).all()

    return [
        CategoryDistribution(
            category=cat.category.value,
            count=cat.count,
            percentage=round((cat.count / total_items) * 100, 2)
        )
        for cat in categories
    ]


# ============================================================================
# USER ACTIVITY ANALYTICS
# ============================================================================

@router.get("/top-users", response_model=list[UserActivity])
async def get_top_users(
        limit: int = Query(10, ge=1, le=50, description="Number of users to return"),
        sort_by: str = Query("total_borrows", regex="^(total_borrows|active_borrows|overdue_items)$"),
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Get most active users by borrowing activity.

    Identifies power users and helps track:
    - Most active borrowers
    - Users with multiple active borrows
    - Users with overdue items

    Args:
        limit: Number of users to return
        sort_by: Sort criteria (total_borrows, active_borrows, overdue_items)
        db: Database session
        current_admin: Authenticated admin user

    Returns:
        List of users with activity metrics
    """
    # Get users with transaction counts
    top_users = db.query(
        User.id,
        User.full_name,
        User.email,
        func.count(Transaction.id).label('total_borrows')
    ).join(
        Transaction, Transaction.user_id == User.id
    ).group_by(
        User.id, User.full_name, User.email
    ).order_by(
        desc('total_borrows')
    ).limit(limit).all()

    result = []
    current_time = datetime.now(UTC)

    for user_data in top_users:
        # Get active borrows count
        active_borrows = db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_data.id,
            Transaction.status == TransactionStatus.BORROWED
        ).scalar() or 0

        # Get overdue items count
        overdue_items = db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_data.id,
            Transaction.status == TransactionStatus.BORROWED,
            Transaction.due_date < current_time
        ).scalar() or 0

        result.append(UserActivity(
            user_id=user_data.id,
            user_name=user_data.full_name,
            user_email=user_data.email,
            total_borrows=user_data.total_borrows,
            active_borrows=active_borrows,
            overdue_items=overdue_items
        ))

    # Sort by requested criteria
    if sort_by == "active_borrows":
        result.sort(key=lambda x: x.active_borrows, reverse=True)
    elif sort_by == "overdue_items":
        result.sort(key=lambda x: x.overdue_items, reverse=True)

    return result


# ============================================================================
# ITEM UTILIZATION
# ============================================================================

@router.get("/item-utilization", response_model=list[ItemUtilization])
async def get_item_utilization(
        limit: int = Query(20, ge=1, le=100),
        category: ItemCategory | None = None,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Get item utilization rates.

    Shows how frequently items are borrowed, helping identify:
    - Underutilized items
    - High-demand items
    - Items that may need replacement or retirement

    Args:
        limit: Number of items to return
        category: Filter by category
        db: Database session
        current_admin: Authenticated admin user

    Returns:
        List of items with utilization metrics
    """
    query = db.query(
        Item.id,
        Item.name,
        Item.item_code,
        Item.category,
        Item.status,
        func.count(Transaction.id).label('borrow_count')
    ).outerjoin(
        Transaction, Transaction.item_id == Item.id
    )

    if category:
        query = query.filter(Item.category == category)

    items = query.group_by(
        Item.id, Item.name, Item.item_code, Item.category, Item.status
    ).order_by(
        desc('borrow_count')
    ).limit(limit).all()

    result = []
    for item in items:
        # Calculate utilization rate (borrows per month since creation)
        item_obj = db.query(Item).filter(Item.id == item.id).first()
        if item_obj:
            created_at = item_obj.created_at
            now = (
                datetime.now(created_at.tzinfo)
                if created_at.tzinfo
                else datetime.now(UTC)
            )
            days_since_creation = (now - created_at).days or 1
            months_since_creation = days_since_creation / 30.0
            utilization_rate = item.borrow_count / months_since_creation if months_since_creation > 0 else 0
        else:
            utilization_rate = 0

        result.append(ItemUtilization(
            item_id=item.id,
            item_name=item.name,
            item_code=item.item_code,
            category=item.category.value,
            total_borrows=item.borrow_count,
            current_status=item.status.value,
            utilization_rate=round(utilization_rate, 2)
        ))

    return result


# ============================================================================
# COMPREHENSIVE OVERVIEW
# ============================================================================

@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Get complete dashboard overview with all key metrics.

    Combines all dashboard data into a single response:
    - Overall statistics
    - Popular items
    - Recent activities
    - Borrowing trends
    - Category distribution
    - Top users

    This is the primary endpoint for rendering admin dashboards.

    Args:
        db: Database session
        current_admin: Authenticated admin user

    Returns:
        Complete dashboard overview object
    """
    # Fetch all dashboard components
    stats = await get_dashboard_stats(db, current_admin)
    popular_items = await get_popular_items(10, None, db, current_admin)
    recent_activities = await get_recent_activities(20, None, db, current_admin)
    borrowing_trends = await get_borrowing_trends(30, db, current_admin)
    category_distribution = await get_category_distribution(db, current_admin)
    top_users = await get_top_users(10, "total_borrows", db, current_admin)

    return DashboardOverview(
        stats=stats,
        popular_items=popular_items,
        recent_activities=recent_activities,
        borrowing_trends=borrowing_trends,
        category_distribution=category_distribution,
        top_users=top_users
    )


# ============================================================================
# HEALTH METRICS
# ============================================================================

@router.get("/health-metrics")
async def get_health_metrics(
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Get system health metrics.

    Provides key indicators of system health:
    - Overdue rate
    - Return rate
    - Issue report rate
    - Request response rate

    Args:
        db: Database session
        current_admin: Authenticated admin user

    Returns:
        Dictionary of health metrics
    """
    current_time = datetime.now(UTC)

    # Total active borrows
    total_active = db.query(func.count(Transaction.id)).filter(
        Transaction.status == TransactionStatus.BORROWED
    ).scalar() or 1

    # Overdue items
    overdue_count = db.query(func.count(Transaction.id)).filter(
        Transaction.status == TransactionStatus.BORROWED,
        Transaction.due_date < current_time
    ).scalar() or 0

    # Total transactions
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 1

    # Returned transactions
    returned_count = db.query(func.count(Transaction.id)).filter(
        Transaction.status == TransactionStatus.RETURNED
    ).scalar() or 0

    # Reviews with issues
    total_reviews = db.query(func.count(Review.id)).scalar() or 1
    reviews_with_issues = db.query(func.count(Review.id)).filter(
        Review.has_issue == True
    ).scalar() or 0

    # Pending requests
    total_requests = db.query(func.count(Request.id)).scalar() or 1
    pending_requests = db.query(func.count(Request.id)).filter(
        Request.status == "pending"
    ).scalar() or 0

    return {
        "overdue_rate": round((overdue_count / total_active) * 100, 2),
        "return_rate": round((returned_count / total_transactions) * 100, 2),
        "issue_report_rate": round((reviews_with_issues / total_reviews) * 100, 2),
        "pending_request_rate": round((pending_requests / total_requests) * 100, 2),
        "total_active_borrows": total_active,
        "total_overdue": overdue_count
    }