"""
Dashboard and Analytics API Endpoints.

Provides statistics, trends, activity insights, and health metrics
for QStock administrators.
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

router = APIRouter(tags=["Dashboard"])


# ============================================================================
# OVERVIEW STATISTICS
# ============================================================================


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardStats:
    """
    Get comprehensive dashboard statistics.

    Provides high-level metrics for users, inventory, transactions,
    reviews, and requests.
    """
    total_users = db.query(func.count(User.id)).scalar() or 0

    active_users = (
        db.query(func.count(User.id))
        .filter(User.is_active.is_(True))
        .scalar()
        or 0
    )

    total_items = db.query(func.count(Item.id)).scalar() or 0

    available_items = (
        db.query(func.count(Item.id))
        .filter(
            Item.status == ItemStatus.AVAILABLE,
            Item.is_borrowable.is_(True),
        )
        .scalar()
        or 0
    )

    borrowed_items = (
        db.query(func.count(Item.id))
        .filter(Item.status == ItemStatus.BORROWED)
        .scalar()
        or 0
    )

    maintenance_items = (
        db.query(func.count(Item.id))
        .filter(Item.status == ItemStatus.MAINTENANCE)
        .scalar()
        or 0
    )

    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0

    active_borrows = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.status == TransactionStatus.BORROWED)
        .scalar()
        or 0
    )

    current_time = datetime.now(UTC)

    overdue_borrows = (
        db.query(func.count(Transaction.id))
        .filter(
            Transaction.status == TransactionStatus.BORROWED,
            Transaction.due_date < current_time,
        )
        .scalar()
        or 0
    )

    total_returns = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.status == TransactionStatus.RETURNED)
        .scalar()
        or 0
    )

    total_reviews = db.query(func.count(Review.id)).scalar() or 0

    pending_requests = (
        db.query(func.count(Request.id))
        .filter(Request.status == "pending")
        .scalar()
        or 0
    )

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
        pending_requests=pending_requests,
    )


# ============================================================================
# POPULAR ITEMS ANALYTICS
# ============================================================================


@router.get("/popular-items", response_model=list[PopularItemsStats])
async def get_popular_items(
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Number of items to return",
    ),
    days: int | None = Query(
        None,
        ge=1,
        description="Filter by last N days",
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> list[PopularItemsStats]:
    """
    Get the most popular items by borrow count.

    Optionally restricts the analysis to borrows from the last N days.
    """
    query = (
        db.query(
            Item.id,
            Item.name,
            Item.item_code,
            Item.category,
            func.count(Transaction.id.distinct()).label("borrow_count"),
            func.avg(Review.rating).label("avg_rating"),
        )
        .join(
            Transaction,
            Transaction.item_id == Item.id,
        )
        .outerjoin(
            Review,
            Review.item_id == Item.id,
        )
    )

    if days is not None:
        date_threshold = datetime.now(UTC) - timedelta(days=days)
        query = query.filter(Transaction.borrowed_at >= date_threshold)

    popular_items = (
        query.group_by(
            Item.id,
            Item.name,
            Item.item_code,
            Item.category,
        )
        .order_by(desc("borrow_count"))
        .limit(limit)
        .all()
    )

    return [
        PopularItemsStats(
            item_id=item.id,
            item_name=item.name,
            item_code=item.item_code,
            category=item.category.value,
            borrow_count=item.borrow_count,
            average_rating=(
                float(item.avg_rating)
                if item.avg_rating is not None
                else None
            ),
        )
        for item in popular_items
    ]


# ============================================================================
# ACTIVITY TRACKING
# ============================================================================


@router.get("/recent-activities", response_model=list[RecentActivity])
async def get_recent_activities(
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of activities to return",
    ),
    activity_types: list[str] | None = Query(
        None,
        description="Filter by activity types: borrow, return, review, request",
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> list[RecentActivity]:
    """
    Get recent system activities for the activity feed.

    Supports filtering by borrow, return, review, and request activities.
    """
    activities: list[RecentActivity] = []

    include_borrows = not activity_types or "borrow" in activity_types
    include_returns = not activity_types or "return" in activity_types
    include_reviews = not activity_types or "review" in activity_types
    include_requests = not activity_types or "request" in activity_types

    # ------------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------------

    if include_borrows or include_returns:
        recent_transactions = (
            db.query(Transaction)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .all()
        )

        for transaction in recent_transactions:
            user = (
                db.query(User)
                .filter(User.id == transaction.user_id)
                .first()
            )

            item = (
                db.query(Item)
                .filter(Item.id == transaction.item_id)
                .first()
            )

            user_name = user.full_name if user else "Unknown User"
            item_name = item.name if item else None
            display_item_name = item_name or "an item"

            if (
                transaction.status == TransactionStatus.BORROWED
                and include_borrows
            ):
                activities.append(
                    RecentActivity(
                        activity_type="borrow",
                        description=f"borrowed {display_item_name}",
                        user_name=user_name,
                        item_name=item_name,
                        timestamp=transaction.borrowed_at,
                    )
                )
            elif (
                transaction.status == TransactionStatus.RETURNED
                and include_returns
            ):
                activities.append(
                    RecentActivity(
                        activity_type="return",
                        description=f"returned {display_item_name}",
                        user_name=user_name,
                        item_name=item_name,
                        timestamp=(
                            transaction.returned_at
                            or transaction.created_at
                        ),
                    )
                )

    # ------------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------------

    if include_reviews:
        recent_reviews = (
            db.query(Review)
            .order_by(Review.created_at.desc())
            .limit(max(1, limit // 2))
            .all()
        )

        for review in recent_reviews:
            user = (
                db.query(User)
                .filter(User.id == review.user_id)
                .first()
            )

            item = (
                db.query(Item)
                .filter(Item.id == review.item_id)
                .first()
            )

            user_name = user.full_name if user else "Unknown User"
            item_name = item.name if item else None
            display_item_name = item_name or "an item"

            if review.has_issue:
                description = (
                    f"reported an issue with {display_item_name}"
                )
            else:
                description = f"reviewed {display_item_name}"

            activities.append(
                RecentActivity(
                    activity_type="review",
                    description=description,
                    user_name=user_name,
                    item_name=item_name,
                    timestamp=review.created_at,
                )
            )

    # ------------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------------

    if include_requests:
        recent_requests = (
            db.query(Request)
            .order_by(Request.created_at.desc())
            .limit(max(1, limit // 2))
            .all()
        )

        for request in recent_requests:
            user = (
                db.query(User)
                .filter(User.id == request.user_id)
                .first()
            )

            activities.append(
                RecentActivity(
                    activity_type="request",
                    description=f"submitted request: {request.title}",
                    user_name=user.full_name if user else "Unknown User",
                    item_name=None,
                    timestamp=request.created_at,
                )
            )

    activities.sort(
        key=lambda activity: activity.timestamp,
        reverse=True,
    )

    return activities[:limit]


# ============================================================================
# TREND ANALYSIS
# ============================================================================


@router.get("/borrowing-trends", response_model=list[BorrowingTrend])
async def get_borrowing_trends(
    days: int = Query(
        30,
        ge=7,
        le=365,
        description="Number of days to analyze",
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> list[BorrowingTrend]:
    """
    Get daily borrowing and return trends for the requested period.
    """
    start_date = datetime.now(UTC) - timedelta(days=days)
    trends: list[BorrowingTrend] = []

    for day_offset in range(days):
        date = start_date + timedelta(days=day_offset)
        next_date = date + timedelta(days=1)

        borrow_count = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.borrowed_at >= date,
                Transaction.borrowed_at < next_date,
            )
            .scalar()
            or 0
        )

        return_count = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.returned_at >= date,
                Transaction.returned_at < next_date,
                Transaction.status == TransactionStatus.RETURNED,
            )
            .scalar()
            or 0
        )

        trends.append(
            BorrowingTrend(
                date=date.strftime("%Y-%m-%d"),
                borrow_count=borrow_count,
                return_count=return_count,
            )
        )

    return trends


# ============================================================================
# CATEGORY ANALYTICS
# ============================================================================


@router.get(
    "/category-distribution",
    response_model=list[CategoryDistribution],
)
async def get_category_distribution(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> list[CategoryDistribution]:
    """
    Get the distribution of inventory items across categories.
    """
    total_items = db.query(func.count(Item.id)).scalar() or 0

    categories = (
        db.query(
            Item.category,
            func.count(Item.id).label("count"),
        )
        .group_by(Item.category)
        .all()
    )

    if total_items == 0:
        return [
            CategoryDistribution(
                category=category.category.value,
                count=category.count,
                percentage=0.0,
            )
            for category in categories
        ]

    return [
        CategoryDistribution(
            category=category.category.value,
            count=category.count,
            percentage=round(
                (category.count / total_items) * 100,
                2,
            ),
        )
        for category in categories
    ]


# ============================================================================
# USER ACTIVITY ANALYTICS
# ============================================================================


@router.get("/top-users", response_model=list[UserActivity])
async def get_top_users(
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Number of users to return",
    ),
    sort_by: str = Query(
        "total_borrows",
        pattern="^(total_borrows|active_borrows|overdue_items)$",
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> list[UserActivity]:
    """
    Get the most active users by borrowing activity.
    """
    top_users = (
        db.query(
            User.id,
            User.full_name,
            User.email,
            func.count(Transaction.id).label("total_borrows"),
        )
        .join(
            Transaction,
            Transaction.user_id == User.id,
        )
        .group_by(
            User.id,
            User.full_name,
            User.email,
        )
        .order_by(desc("total_borrows"))
        .limit(limit)
        .all()
    )

    current_time = datetime.now(UTC)
    result: list[UserActivity] = []

    for user_data in top_users:
        active_borrows = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.user_id == user_data.id,
                Transaction.status == TransactionStatus.BORROWED,
            )
            .scalar()
            or 0
        )

        overdue_items = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.user_id == user_data.id,
                Transaction.status == TransactionStatus.BORROWED,
                Transaction.due_date < current_time,
            )
            .scalar()
            or 0
        )

        result.append(
            UserActivity(
                user_id=user_data.id,
                user_name=user_data.full_name,
                user_email=user_data.email,
                total_borrows=user_data.total_borrows,
                active_borrows=active_borrows,
                overdue_items=overdue_items,
            )
        )

    if sort_by == "active_borrows":
        result.sort(
            key=lambda user: user.active_borrows,
            reverse=True,
        )
    elif sort_by == "overdue_items":
        result.sort(
            key=lambda user: user.overdue_items,
            reverse=True,
        )

    return result


# ============================================================================
# ITEM UTILIZATION
# ============================================================================


@router.get("/item-utilization", response_model=list[ItemUtilization])
async def get_item_utilization(
    limit: int = Query(20, ge=1, le=100),
    category: ItemCategory | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> list[ItemUtilization]:
    """
    Get item utilization rates based on borrowing frequency.
    """
    query = (
        db.query(
            Item.id,
            Item.name,
            Item.item_code,
            Item.category,
            Item.status,
            func.count(Transaction.id).label("borrow_count"),
        )
        .outerjoin(
            Transaction,
            Transaction.item_id == Item.id,
        )
    )

    if category is not None:
        query = query.filter(Item.category == category)

    items = (
        query.group_by(
            Item.id,
            Item.name,
            Item.item_code,
            Item.category,
            Item.status,
        )
        .order_by(desc("borrow_count"))
        .limit(limit)
        .all()
    )

    result: list[ItemUtilization] = []

    for item in items:
        item_obj = (
            db.query(Item)
            .filter(Item.id == item.id)
            .first()
        )

        utilization_rate = 0.0

        if item_obj is not None:
            created_at = item_obj.created_at

            if created_at.tzinfo is not None:
                now = datetime.now(created_at.tzinfo)
            else:
                now = datetime.now(UTC)

            days_since_creation = max(
                (now - created_at).days,
                1,
            )

            months_since_creation = days_since_creation / 30.0
            utilization_rate = item.borrow_count / months_since_creation

        result.append(
            ItemUtilization(
                item_id=item.id,
                item_name=item.name,
                item_code=item.item_code,
                category=item.category.value,
                total_borrows=item.borrow_count,
                current_status=item.status.value,
                utilization_rate=round(utilization_rate, 2),
            )
        )

    return result


# ============================================================================
# COMPREHENSIVE OVERVIEW
# ============================================================================


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> DashboardOverview:
    """
    Get the complete dashboard overview.

    Combines statistics, popular items, recent activity, borrowing trends,
    category distribution, and top-user activity into a single response.
    """
    stats = await get_dashboard_stats(
        db=db,
        current_user=current_admin,
    )

    popular_items = await get_popular_items(
        limit=10,
        days=None,
        db=db,
        current_admin=current_admin,
    )

    recent_activities = await get_recent_activities(
        limit=20,
        activity_types=None,
        db=db,
        current_admin=current_admin,
    )

    borrowing_trends = await get_borrowing_trends(
        days=30,
        db=db,
        current_admin=current_admin,
    )

    category_distribution = await get_category_distribution(
        db=db,
        current_admin=current_admin,
    )

    top_users = await get_top_users(
        limit=10,
        sort_by="total_borrows",
        db=db,
        current_admin=current_admin,
    )

    return DashboardOverview(
        stats=stats,
        popular_items=popular_items,
        recent_activities=recent_activities,
        borrowing_trends=borrowing_trends,
        category_distribution=category_distribution,
        top_users=top_users,
    )


# ============================================================================
# HEALTH METRICS
# ============================================================================


@router.get("/health-metrics")
async def get_health_metrics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> dict[str, float | int]:
    """
    Get system health metrics.

    Provides overdue, return, issue-report, and pending-request rates.
    """
    current_time = datetime.now(UTC)

    total_active = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.status == TransactionStatus.BORROWED)
        .scalar()
        or 0
    )

    overdue_count = (
        db.query(func.count(Transaction.id))
        .filter(
            Transaction.status == TransactionStatus.BORROWED,
            Transaction.due_date < current_time,
        )
        .scalar()
        or 0
    )

    total_transactions = (
        db.query(func.count(Transaction.id)).scalar()
        or 0
    )

    returned_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.status == TransactionStatus.RETURNED)
        .scalar()
        or 0
    )

    total_reviews = db.query(func.count(Review.id)).scalar() or 0

    reviews_with_issues = (
        db.query(func.count(Review.id))
        .filter(Review.has_issue.is_(True))
        .scalar()
        or 0
    )

    total_requests = db.query(func.count(Request.id)).scalar() or 0

    pending_requests = (
        db.query(func.count(Request.id))
        .filter(Request.status == "pending")
        .scalar()
        or 0
    )

    overdue_rate = (
        round((overdue_count / total_active) * 100, 2)
        if total_active
        else 0.0
    )

    return_rate = (
        round((returned_count / total_transactions) * 100, 2)
        if total_transactions
        else 0.0
    )

    issue_report_rate = (
        round((reviews_with_issues / total_reviews) * 100, 2)
        if total_reviews
        else 0.0
    )

    pending_request_rate = (
        round((pending_requests / total_requests) * 100, 2)
        if total_requests
        else 0.0
    )

    return {
        "overdue_rate": overdue_rate,
        "return_rate": return_rate,
        "issue_report_rate": issue_report_rate,
        "pending_request_rate": pending_request_rate,
        "total_active_borrows": total_active,
        "total_overdue": overdue_count,
    }