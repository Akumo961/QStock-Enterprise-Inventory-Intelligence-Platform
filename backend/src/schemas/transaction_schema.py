"""
transaction_schema.py — ORDERS + QR WORKFLOW

Transaction schemas preserved.
Orders to support:
- new_item
- special_borrow
- other

Order statuses restricted to:
- pending
- approved
- rejected
- ready

Added bulk QR borrow/return schemas required for
admin borrow-to-user and multi-item return workflows.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.transaction import (
    OrderStatus,
    OrderType,
    TransactionStatus,
)

# =============================================================================
# TRANSACTIONS
# =============================================================================

class TransactionBase(BaseModel):
    quantity: int = Field(default=1, ge=1)
    purpose: str | None = None
    notes: str | None = None


class TransactionCreate(TransactionBase):
    # Optional: omit to borrow for self; provide to borrow on behalf of another user (admin only)
    user_qr_code: str | None = Field(
        None,
        description="User QR code data. Omit to borrow for self."
    )

    item_qr_code: str = Field(
        ...,
        description="Item QR code data"
    )

    due_days: int | None = Field(
        None,
        ge=1
    )


class TransactionReturn(BaseModel):
    transaction_id: int

    condition_at_return: str | None = Field(
        None,
        max_length=50
    )

    notes: str | None = None


class TransactionUpdate(BaseModel):
    status: TransactionStatus | None = None
    due_date: datetime | None = None
    notes: str | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    item_id: int

    status: TransactionStatus

    quantity: int

    borrowed_at: datetime

    due_date: datetime | None = None

    returned_at: datetime | None = None

    purpose: str | None = None

    notes: str | None = None

    condition_at_borrow: str | None = None

    condition_at_return: str | None = None

    created_at: datetime
    updated_at: datetime


class TransactionDetailResponse(TransactionResponse):
    user_name: str
    user_email: str

    item_name: str
    item_code: str


class TransactionListResponse(BaseModel):
    transactions: list[TransactionDetailResponse]

    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# QR BORROW / RETURN
# =============================================================================

class QRBorrowRequest(BaseModel):
    """
    Standard borrow request.

    User:
        user_qr_code omitted (borrow for self)

    Admin:
        user_qr_code provided (borrow for another user)
    """

    user_qr_code: str | None = Field(
        None,
        description="Omit to borrow for self"
    )

    item_qr_code: str

    quantity: int = Field(
        default=1,
        ge=1
    )

    purpose: str | None = None

    due_days: int | None = Field(
        None,
        ge=1
    )


class QRBulkBorrowRequest(BaseModel):
    """
    Admin workflow:

    1. Scan user card
    2. Scan multiple inventory items
    3. Assign all items
    """

    user_qr_code: str

    item_qr_codes: list[str] = Field(
        min_length=1
    )

    purpose: str | None = None

    due_days: int | None = Field(
        None,
        ge=1
    )


class QRReturnRequest(BaseModel):
    """
    Standard return request.

    User:
        scan item and return own loan.

    Admin:
        may optionally provide user card QR.
    """

    item_qr_code: str

    user_qr_code: str | None = Field(
        None,
        description="Omit to return your own item"
    )

    condition_at_return: str | None = Field(
        default="good",
        max_length=50
    )

    notes: str | None = None


class QRBulkReturnRequest(BaseModel):
    """
    Admin workflow:

    1. Scan returned items
    2. Scan user card
    3. Return all items
    """

    user_qr_code: str

    item_qr_codes: list[str] = Field(
        min_length=1
    )

    condition_at_return: str | None = Field(
        default="good",
        max_length=50
    )

    notes: str | None = None


# =============================================================================
# ORDERS
# =============================================================================

class OrderCreate(BaseModel):
    """
    User creates an order.

    Required:
    - order_type
    - description

    Optional:
    - item_id
    - needed_date

    Title is optional and may be auto-generated
    by backend service.
    """

    order_type: OrderType

    description: str = Field(
        ...,
        min_length=1
    )

    title: str | None = Field(
        None,
        max_length=255
    )

    item_id: int | None = None

    needed_date: datetime | None = None


class OrderUpdate(BaseModel):
    """
    Admin updates order.
    """

    status: OrderStatus | None = None

    admin_response: str | None = Field(
        None,
        max_length=1000
    )

    ready_date: datetime | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    user_id: int

    order_type: OrderType

    title: str | None = None

    description: str

    item_id: int | None = None

    needed_date: datetime | None = None

    ready_date: datetime | None = None

    status: OrderStatus

    admin_response: str | None = None

    responded_by_admin_id: int | None = None

    responded_at: datetime | None = None

    created_at: datetime

    updated_at: datetime

    # Enriched fields
    user_name: str = ""

    user_email: str = ""

    user_employee_id: str | None = None

    item_name: str | None = None

    admin_name: str | None = None


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]

    total: int

    page: int

    page_size: int

    total_pages: int


# =============================================================================
# LEGACY COMPATIBILITY ALIASES
# =============================================================================

RequestCreate = OrderCreate
RequestUpdate = OrderUpdate

# Older endpoints expect these names
RequestResponse = OrderResponse
RequestDetailResponse = OrderResponse
RequestListResponse = OrderListResponse