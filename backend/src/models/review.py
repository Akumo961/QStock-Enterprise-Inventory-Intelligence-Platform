from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class Review(BaseModel):
    """Review/Feedback model for borrowed items"""

    __tablename__ = "reviews"

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)

    # Review Details
    rating = Column(Integer, nullable=True)  # 1-5 stars (optional)
    comment = Column(Text, nullable=True)

    # Issue Reporting
    has_issue = Column(Boolean, default=False, nullable=False)
    issue_type = Column(String(100), nullable=True)  # damage, missing_parts, malfunction, etc.
    issue_description = Column(Text, nullable=True)
    issue_severity = Column(String(20), nullable=True)  # minor, moderate, severe

    # Admin Response
    admin_notified = Column(Boolean, default=False, nullable=False)
    admin_response = Column(Text, nullable=True)
    issue_resolved = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="reviews")
    item = relationship("Item", back_populates="reviews")
    transaction = relationship("Transaction")

    def __repr__(self):
        return f"<Review(id={self.id}, user_id={self.user_id}, item_id={self.item_id}, has_issue={self.has_issue})>"