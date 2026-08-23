"""
Pydantic Schemas Package

Contains all Pydantic models for request/response validation.
"""

# ============================================================================
# USER SCHEMAS
# ============================================================================

# ============================================================================
# ITEM SCHEMAS
# ============================================================================
from src.schemas.item_schema import (
    ItemAvailability,
    ItemBase,
    ItemCreate,
    ItemListResponse,
    ItemQRCode,
    ItemResponse,
    ItemStats,
    ItemUpdate,
    PopularItem,
)

# ============================================================================
# REVIEW SCHEMAS
# ============================================================================
from src.schemas.review_schema import (
    ReviewBase,
    ReviewCreate,
    ReviewDetailResponse,
    ReviewListResponse,
    ReviewResponse,
    ReviewUpdate,
)

# ============================================================================
# TRANSACTION / ORDER SCHEMAS
# ============================================================================
from src.schemas.transaction_schema import (
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    OrderUpdate,
    RequestCreate,
    RequestDetailResponse,
    RequestListResponse,
    RequestResponse,
    RequestUpdate,
    TransactionBase,
    TransactionCreate,
    TransactionDetailResponse,
    TransactionListResponse,
    TransactionResponse,
    TransactionReturn,
    TransactionUpdate,
)
from src.schemas.user_schema import (
    UserBase,
    UserChangePassword,
    UserCreate,
    UserListResponse,
    UserQRCode,
    UserResponse,
    UserStats,
    UserUpdate,
)

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "ItemAvailability",
    "ItemBase",
    "ItemCreate",
    "ItemListResponse",
    "ItemQRCode",
    "ItemResponse",
    "ItemStats",
    "ItemUpdate",
    "OrderCreate",
    "OrderListResponse",
    "OrderResponse",
    "OrderUpdate",
    "PopularItem",
    "QRBorrowRequest",
    "QRBulkBorrowRequest",
    "QRBulkReturnRequest",
    "QRReturnRequest",
    "RequestCreate",
    "RequestDetailResponse",
    "RequestListResponse",
    "RequestResponse",
    "RequestUpdate",
    "ReviewBase",
    "ReviewCreate",
    "ReviewDetailResponse",
    "ReviewListResponse",
    "ReviewResponse",
    "ReviewUpdate",
    "TransactionBase",
    "TransactionCreate",
    "TransactionDetailResponse",
    "TransactionListResponse",
    "TransactionResponse",
    "TransactionReturn",
    "TransactionUpdate",
    "UserBase",
    "UserChangePassword",
    "UserCreate",
    "UserListResponse",
    "UserQRCode",
    "UserResponse",
    "UserStats",
    "UserUpdate",
]