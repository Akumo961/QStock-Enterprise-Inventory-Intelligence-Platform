import enum

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class ItemStatus(str, enum.Enum):
    """Inventory item status enum — values MUST match DB exactly (lowercase)"""
    AVAILABLE = "available"
    BORROWED = "borrowed"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class ItemCategory(str, enum.Enum):
    """Scout-specific inventory category enum — values MUST match DB exactly (lowercase)"""
    ELECTRONICS = "electronics"
    SCHOOL_ITEMS = "school_items"
    DECORATIONS = "decorations"
    CLOTHES = "clothes"
    GAMES = "games"
    OTHER = "other"


class Item(BaseModel):
    """Inventory Item model"""

    __tablename__ = "items"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    item_code = Column(String(100), unique=True, index=True, nullable=False)
    qr_code_data = Column(String(500), unique=True, nullable=False)
    qr_code_image = Column(Text, nullable=True)
    category = Column(SQLEnum(ItemCategory, values_callable=lambda obj: [e.value for e in obj],
                              native_enum=False, create_constraint=False),
                      default=ItemCategory.OTHER, nullable=False)
    status = Column(SQLEnum(ItemStatus, values_callable=lambda obj: [e.value for e in obj],
                            native_enum=False, create_constraint=False),
                    default=ItemStatus.AVAILABLE, nullable=False)
    serial_number = Column(String(100), unique=True, nullable=True)
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    purchase_date = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    available_quantity = Column(Integer, default=1, nullable=False)
    is_borrowable = Column(Boolean, default=True, nullable=False)
    requires_approval = Column(Boolean, default=False, nullable=False)
    max_borrow_days = Column(Integer, default=7, nullable=True)
    notes = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    transactions = relationship("Transaction", back_populates="item", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item(id={self.id}, code='{self.item_code}', name='{self.name}', status='{self.status}')>"
