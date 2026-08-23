from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class User(BaseModel):
    """User/Employee model"""

    __tablename__ = "users"

    # Basic Information
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # QR Code
    qr_code_data = Column(String(500), unique=True, nullable=False)
    qr_code_image = Column(Text, nullable=True)

    # Status & Permissions
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Optional Fields
    department = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=False)
    employee_id = Column(String(50), unique=True, nullable=True)

    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================

    transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    approved_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.approved_by_admin_id",
        back_populates="approved_by",
    )

    reviews = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Changed Request -> Order
    requests = relationship(
        "Order",
        foreign_keys="Order.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    approved_requests = relationship(
        "Order",
        foreign_keys="Order.responded_by_admin_id",
        back_populates="responded_by",
    )

    def __repr__(self):
        return (
            f"<User(id={self.id}, "
            f"email='{self.email}', "
            f"name='{self.full_name}')>"
        )