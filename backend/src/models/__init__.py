"""
Database Models Package

Contains all SQLAlchemy ORM models for the QR Inventory System.
All models inherit from the Base class and include automatic timestamps.
"""

from src.models.base import BaseModel
from src.models.item import Item, ItemCategory, ItemStatus
from src.models.review import Review
from src.models.transaction import (
    Order,
    OrderStatus,
    Transaction,
    TransactionStatus,
)
from src.models.user import User

__all__ = [
    "BaseModel",
    "Item",
    "ItemCategory",
    "ItemStatus",
    "Order",
    "OrderStatus",
    "Review",
    "Transaction",
    "TransactionStatus",
    "User",
]

# Model registry for migrations and database initialization.
MODELS = [
    User,
    Item,
    Transaction,
    Order,
    Review,
]