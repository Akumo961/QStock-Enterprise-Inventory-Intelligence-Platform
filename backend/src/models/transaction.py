"""
transaction.py

Inventory Transactions + Orders

Updated to support:

Transactions
------------
- borrowed
- returned
- overdue
- cancelled

Orders
------
- new_item
- special_borrow
- other

Order statuses
--------------
- pending
- approved
- rejected
- ready

Notes
-----
- Preserves existing table name "requests" for backward compatibility.
- Preserves legacy columns request_type and priority.
- Preserves Request alias for existing imports.
"""

from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import BaseModel

# =============================================================================
# ENUMS
# =============================================================================

class OrderStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    READY = "ready"


class OrderType(str, Enum):
    NEW_ITEM = "new_item"
    SPECIAL_BORROW = "special_borrow"
    OTHER = "other"


class TransactionStatus(str, Enum):
    BORROWED = "borrowed"
    RETURNED = "returned"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


# =============================================================================
# TRANSACTIONS
# =============================================================================

class Transaction(BaseModel):
    __tablename__ = "transactions"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    item_id = Column(
        Integer,
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        SQLEnum(
            TransactionStatus,
            values_callable=_enum_values,
            native_enum=False,
        ),
        default=TransactionStatus.BORROWED,
        nullable=False,
    )

    quantity = Column(
        Integer,
        default=1,
        nullable=False,
    )

    borrowed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    due_date = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    returned_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    purpose = Column(
        Text,
        nullable=True,
    )

    notes = Column(
        Text,
        nullable=True,
    )

    approved_by_admin_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    condition_at_borrow = Column(
        String(50),
        default="good",
        nullable=True,
    )

    condition_at_return = Column(
        String(50),
        nullable=True,
    )

    # Relationships

    user = relationship(
        "User",
        back_populates="transactions",
        foreign_keys=[user_id],
    )

    item = relationship(
        "Item",
        back_populates="transactions",
    )

    approved_by = relationship(
        "User",
        foreign_keys=[approved_by_admin_id],
    )

    def __repr__(self):
        return (
            f"<Transaction("
            f"id={self.id}, "
            f"status='{self.status.value}'"
            f")>"
        )


# =============================================================================
# ORDERS
# =============================================================================

class Order(BaseModel):
    """
    Orders (formerly Request)

    Allowed order types:
        - new_item
        - special_borrow
        - other

    Allowed statuses:
        - pending
        - approved
        - rejected
        - ready
    """

    __tablename__ = "requests"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    item_id = Column(
        Integer,
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Order Details
    # -------------------------------------------------------------------------

    order_type = Column(
        SQLEnum(
            OrderType,
            values_callable=_enum_values,
            native_enum=False,
        ),
        nullable=False,
        default=OrderType.OTHER,
    )

    # Optional title.
    # Can be auto-generated from order type by service layer.
    title = Column(
        String(255),
        nullable=True,
    )

    description = Column(
        Text,
        nullable=False,
    )

    # User requested date
    needed_date = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Admin marks ready date
    ready_date = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    status = Column(
        SQLEnum(
            OrderStatus,
            values_callable=_enum_values,
            native_enum=False,
        ),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Admin Response
    # -------------------------------------------------------------------------

    admin_response = Column(
        Text,
        nullable=True,
    )

    responded_by_admin_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    responded_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Legacy Columns
    # -------------------------------------------------------------------------
    # Kept to avoid breaking existing DB structure.
    # Do not remove without migration.

    request_type = Column(
        String(50),
        nullable=True,
    )

    priority = Column(
        String(20),
        default="normal",
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    user = relationship(
        "User",
        back_populates="requests",
        foreign_keys=[user_id],
    )

    item = relationship(
        "Item",
    )

    responded_by = relationship(
        "User",
        foreign_keys=[responded_by_admin_id],
    )

    def __repr__(self):
        return (
            f"<Order("
            f"id={self.id}, "
            f"type='{self.order_type.value}', "
            f"status='{self.status.value}'"
            f")>"
        )


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

Request = Order