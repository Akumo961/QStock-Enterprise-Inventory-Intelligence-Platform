"""
Dashboard Schemas
"""


from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_users: int
    active_users: int

    total_items: int
    available_items: int
    borrowed_items: int
    maintenance_items: int

    total_transactions: int
    active_borrows: int
    overdue_borrows: int
    total_returns: int

    total_reviews: int
    pending_requests: int


class PopularItemsStats(BaseModel):
    item_id: int
    item_name: str
    item_code: str
    category: str
    borrow_count: int
    average_rating: float | None = None


class RecentActivity(BaseModel):
    activity_type: str
    description: str
    user_name: str
    item_name: str | None = None
    timestamp: str | object


class BorrowingTrend(BaseModel):
    date: str
    borrow_count: int
    return_count: int


class CategoryDistribution(BaseModel):
    category: str
    count: int
    percentage: float


class UserActivity(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    total_borrows: int
    active_borrows: int
    overdue_items: int


class ItemUtilization(BaseModel):
    item_id: int
    item_name: str
    item_code: str
    category: str
    total_borrows: int
    current_status: str
    utilization_rate: float


class DashboardOverview(BaseModel):
    stats: DashboardStats
    popular_items: list[PopularItemsStats]
    recent_activities: list[RecentActivity]
    borrowing_trends: list[BorrowingTrend]
    category_distribution: list[CategoryDistribution]
    top_users: list[UserActivity]


# Legacy import compatibility
class RequestBase(BaseModel):
    pass