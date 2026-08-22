"""
Core Package

Contains core application functionality including:
- Configuration management
- Database setup
- Security and authentication
- QR code generation
"""

from src.core.config import settings
from src.core.database import Base, SessionLocal, engine, get_db, init_db
from src.core.qr_generator import QRCodeGenerator, qr_generator
from src.core.security import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_current_admin_user,
    get_current_user,
    get_password_hash,
    verify_password,
)

__all__ = [
    "Base",
    "QRCodeGenerator",
    "SessionLocal",
    "authenticate_user",
    "create_access_token",
    "decode_access_token",
    "engine",
    "get_current_admin_user",
    "get_current_user",
    "get_db",
    "get_password_hash",
    "init_db",
    "qr_generator",
    "settings",
    "verify_password",
]