"""
Main FastAPI application for QR Code Inventory Management System
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.api.endpoints.ai import router as ai_router
from src.api.endpoints.auth import router as auth_router
from src.api.endpoints.dashboard import router as dashboard_router
from src.api.endpoints.items import router as items_router
from src.api.endpoints.orders import router as orders_router
from src.api.endpoints.reports import router as reports_router
from src.api.endpoints.reviews import router as reviews_router
from src.api.endpoints.transactions import router as transactions_router
from src.api.endpoints.users import router as users_router
from src.core.config import settings
from src.core.database import engine, get_db, init_db
from src.core.qr_generator import qr_generator
from src.core.security import get_password_hash
from src.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    print("🚀 Starting QR Inventory System API...")

    # Initialize database
    print("📦 Initializing database...")
    init_db()

    # Create initial admin user if doesn't exist
    print("👤 Checking for initial admin user...")
    db = next(get_db())

    try:
        admin = (
            db.query(User)
            .filter(User.email == settings.INITIAL_ADMIN_EMAIL)
            .first()
        )

        if not admin:
            print("🔧 Creating initial admin user...")
            hashed_password = get_password_hash(
                settings.INITIAL_ADMIN_PASSWORD
            )

            admin = User(
                email=settings.INITIAL_ADMIN_EMAIL,
                full_name=settings.INITIAL_ADMIN_NAME,
                hashed_password=hashed_password,
                phone=settings.INITIAL_ADMIN_PHONE,
                is_admin=True,
                is_active=True,
                qr_code_data="temp",
            )

            db.add(admin)
            db.commit()
            db.refresh(admin)

            # Generate QR code
            qr_code_data = qr_generator.generate_user_qr_data(
                admin.id,
                admin.email,
            )
            qr_code_image = qr_generator.generate_qr_code_base64(
                qr_code_data
            )

            admin.qr_code_data = qr_code_data
            admin.qr_code_image = qr_code_image

            db.commit()

            print(
                f"✅ Initial admin created: "
                f"{settings.INITIAL_ADMIN_EMAIL}"
            )
            print(
                f"⚠️  Default password: "
                f"{settings.INITIAL_ADMIN_PASSWORD}"
            )
            print("⚠️  Please change the password after first login!")
        else:
            print("✅ Admin user already exists")

    finally:
        db.close()

    print("✅ Application startup complete!")

    yield

    # Shutdown
    print("👋 Shutting down QR Inventory System API...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "QR Code-based Inventory Management System "
        "for employee borrowing and tracking"
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    try:
        # Check database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        db_status = "connected"
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc!s}"

    return {
        "status": "healthy",
        "database": db_status,
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# Include routers
app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"],
)
app.include_router(
    users_router,
    prefix="/api/users",
    tags=["Users"],
)
app.include_router(
    items_router,
    prefix="/api/items",
    tags=["Items"],
)
app.include_router(
    transactions_router,
    prefix="/api/transactions",
    tags=["Transactions"],
)
app.include_router(
    orders_router,
    prefix="/api/orders",
    tags=["Orders"],
)
app.include_router(
    dashboard_router,
    prefix="/api/dashboard",
    tags=["Dashboard"],
)
app.include_router(
    reviews_router,
    prefix="/api/reviews",
    tags=["Reviews"],
)
app.include_router(
    ai_router,
    prefix="/api/ai",
    tags=["AI Assistant"],
)
app.include_router(
    reports_router,
    prefix="/api/reports",
    tags=["Reports"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all uncaught exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": (
                str(exc)
                if settings.DEBUG
                else "An error occurred"
            ),
        },
    )


# Custom 404 handler
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Resource not found"},
    )


if __name__ == "__main__":
    import uvicorn

    print(
        f"🌐 Starting {settings.APP_NAME} "
        f"v{settings.APP_VERSION}"
    )
    print(f"📍 Environment: {settings.ENVIRONMENT}")
    print(f"🔧 Debug mode: {settings.DEBUG}")

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )