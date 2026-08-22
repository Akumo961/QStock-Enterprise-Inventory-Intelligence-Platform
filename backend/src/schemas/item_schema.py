from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.item import ItemCategory, ItemStatus


class ItemBase(BaseModel):
    """Base item schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: ItemCategory = ItemCategory.OTHER
    serial_number: str | None = Field(None, max_length=100)
    brand: str | None = Field(None, max_length=100)
    model: str | None = Field(None, max_length=100)
    purchase_date: str | None = None
    location: str | None = Field(None, max_length=255)
    quantity: int = Field(default=1, ge=1)
    is_borrowable: bool = True
    requires_approval: bool = False
    max_borrow_days: int | None = Field(default=7, ge=1)
    notes: str | None = None
    image_url: str | None = None

    # Accept both "OTHER" and "other" from frontend — normalise to lowercase
    @field_validator('category', mode='before')
    @classmethod
    def normalise_category(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class ItemCreate(ItemBase):
    """Schema for creating a new item"""
    item_code: str | None = Field(None, max_length=100)
    available_quantity: int | None = Field(
        None, ge=0,
        description="How many of `quantity` are available right now. Defaults to the full quantity if omitted. Cannot exceed quantity.",
    )


class ItemUpdate(BaseModel):
    """Schema for updating an item — item_code excluded (read-only after creation)"""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: ItemCategory | None = None
    status: ItemStatus | None = None
    serial_number: str | None = Field(None, max_length=100)
    brand: str | None = Field(None, max_length=100)
    model: str | None = Field(None, max_length=100)
    purchase_date: str | None = None
    location: str | None = Field(None, max_length=255)
    quantity: int | None = Field(None, ge=1)
    available_quantity: int | None = Field(None, ge=0)
    is_borrowable: bool | None = None
    requires_approval: bool | None = None
    max_borrow_days: int | None = Field(None, ge=1)
    notes: str | None = None
    image_url: str | None = None

    @field_validator('category', mode='before')
    @classmethod
    def normalise_category(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator('status', mode='before')
    @classmethod
    def normalise_status(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class ItemResponse(ItemBase):
    """Schema for item response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_code: str
    qr_code_data: str
    qr_code_image: str | None = None
    status: ItemStatus
    available_quantity: int
    created_at: datetime
    updated_at: datetime


class ItemQRCode(BaseModel):
    """Schema for item QR code information"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_code: str
    name: str
    qr_code_data: str
    qr_code_image: str


class ItemListResponse(BaseModel):
    """Schema for paginated item list"""
    items: list[ItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ItemStats(BaseModel):
    """Schema for item statistics"""
    total_borrows: int
    current_borrowed: int
    total_returns: int
    average_rating: float | None = None
    total_reviews: int
    times_reported: int


class PopularItem(BaseModel):
    """Schema for popular item statistics"""
    item_id: int
    item_name: str
    item_code: str
    borrow_count: int
    category: str


class ItemAvailability(BaseModel):
    """Schema for checking item availability"""
    item_id: int
    is_available: bool
    available_quantity: int
    total_quantity: int
    status: ItemStatus
    next_available_date: datetime | None = None