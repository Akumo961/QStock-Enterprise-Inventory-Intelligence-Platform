from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewBase(BaseModel):
    """Base review schemas"""
    rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = None
    has_issue: bool = False
    issue_type: str | None = Field(None, max_length=100)
    issue_description: str | None = None
    issue_severity: str | None = Field(None, pattern="^(minor|moderate|severe)$")


class ReviewCreate(ReviewBase):
    """Schema for creating a new review"""
    item_id: int
    transaction_id: int | None = None


class ReviewUpdate(BaseModel):
    """Schema for updating a review"""
    rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = None
    admin_response: str | None = None
    issue_resolved: bool | None = None


class ReviewResponse(BaseModel):
    """Schema for review response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    item_id: int
    transaction_id: int | None = None
    rating: int | None = None
    comment: str | None = None
    has_issue: bool
    issue_type: str | None = None
    issue_description: str | None = None
    issue_severity: str | None = None
    admin_notified: bool
    admin_response: str | None = None
    issue_resolved: bool
    created_at: datetime
    updated_at: datetime


class ReviewDetailResponse(ReviewResponse):
    """Schema for detailed review response"""
    user_name: str
    user_email: str
    item_name: str
    item_code: str


class ReviewListResponse(BaseModel):
    """Schema for paginated review list"""
    reviews: list[ReviewDetailResponse]
    total: int
    page: int
    page_size: int
    total_pages: int