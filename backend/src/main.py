"""
QStock - QR Inventory Management System
Main FastAPI application
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

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

logger = logging.getLogger(__name__)

# ============================================================
# STARTUP / SHUTDOWN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("🚀 Starting QStock API...")

    # -------------------------
    # Database initialization
    # -------------------------

    try:
        print("📦 Initializing database...")
        init_db()


    except SQLAlchemyError:

        logger.exception(

            "Database initialization failed"
        )


    # -------------------------
    # Initial admin creation
    # -------------------------

    print("👤 Checking initial administrator...")


    db = next(get_db())


    try:

        if not settings.INITIAL_ADMIN_EMAIL:

            print(
                "⚠️ INITIAL_ADMIN_EMAIL missing. "
                "Skipping admin creation."
            )


        else:

            existing_admin = (
                db.query(User)
                .filter(
                    User.email ==
                    settings.INITIAL_ADMIN_EMAIL
                )
                .first()
            )


            if existing_admin:

                print(
                    f"✅ Admin already exists: "
                    f"{existing_admin.email}"
                )


            else:

                print("🔧 Creating initial admin...")


                admin = User(

                    email=settings.INITIAL_ADMIN_EMAIL,

                    full_name=settings.INITIAL_ADMIN_NAME,

                    hashed_password=
                        get_password_hash(
                            settings.INITIAL_ADMIN_PASSWORD
                        ),

                    phone=settings.INITIAL_ADMIN_PHONE,

                    is_admin=True,

                    is_active=True,

                    # Temporary valid unique value
                    qr_code_data=
                        f"INITIAL-{settings.INITIAL_ADMIN_EMAIL}",

                    qr_code_image=""

                )


                db.add(admin)

                db.commit()

                db.refresh(admin)



                # Generate final QR
                qr_data = (
                    qr_generator
                    .generate_user_qr_data(
                        admin.id,
                        admin.email
                    )
                )


                qr_image = (
                    qr_generator
                    .generate_qr_code_base64(
                        qr_data
                    )
                )


                admin.qr_code_data = qr_data

                admin.qr_code_image = qr_image


                db.commit()


                print(
                    "✅ Initial admin created successfully"
                )

                print(
                    f"📧 Email: "
                    f"{settings.INITIAL_ADMIN_EMAIL}"
                )

                print(
                    "🔑 Initial admin password configured"
                )



    except SQLAlchemyError:

        db.rollback()

        logger.exception(

            "Admin setup failed"

        )


    finally:

        db.close()



    print("✅ QStock startup completed")


    yield



    print("👋 QStock shutdown")





# ============================================================
# FASTAPI APPLICATION
# ============================================================


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,

    description=(
        """
        QStock Inventory Intelligence Platform.
        QR-based inventory management with AI assistant.
        """
    ),

    lifespan=lifespan,

    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)


# ============================================================
# CORS
# ============================================================


app.add_middleware(

    CORSMiddleware,

    allow_origins=
        settings.BACKEND_CORS_ORIGINS,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)





# ============================================================
# HEALTH
# ============================================================


@app.get("/")
async def root():

    return {

        "status": "healthy",

        "app": settings.APP_NAME,

        "version": settings.APP_VERSION

    }




@app.get("/health")
async def health_check():

    try:

        with engine.connect() as conn:

            conn.execute(
                text("SELECT 1")
            )


        database="connected"


    except SQLAlchemyError:

        database="error"



    return {

        "status":"healthy",

        "database":database,

        "app_name":
            settings.APP_NAME,

        "version":
            settings.APP_VERSION

    }





# ============================================================
# ROUTERS
# ============================================================


app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"]
)


app.include_router(
    users_router,
    prefix="/api/users",
    tags=["Users"]
)


app.include_router(
    items_router,
    prefix="/api/items",
    tags=["Items"]
)


app.include_router(
    transactions_router,
    prefix="/api/transactions",
    tags=["Transactions"]
)


app.include_router(
    orders_router,
    prefix="/api/orders",
    tags=["Orders"]
)


app.include_router(
    dashboard_router,
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


app.include_router(
    reviews_router,
    prefix="/api/reviews",
    tags=["Reviews"]
)


app.include_router(
    ai_router,
    prefix="/api/ai",
    tags=["AI Assistant"]
)


app.include_router(
    reports_router,
    prefix="/api/reports",
    tags=["Reports"]
)





# ============================================================
# ERRORS
# ============================================================


@app.exception_handler(Exception)
async def global_exception_handler(
    request,
    exc
):

    return JSONResponse(

        status_code=
            status.HTTP_500_INTERNAL_SERVER_ERROR,

        content={

            "detail":
                "Internal server error",

            "error":
                str(exc)
                if settings.DEBUG
                else None

        }

    )




@app.exception_handler(404)
async def not_found_handler(
    request,
    exc
):

    return JSONResponse(

        status_code=404,

        content={
            "detail":
                "Resource not found"
        }

    )





# ============================================================
# LOCAL RUN
# ============================================================


if __name__ == "__main__":

    import uvicorn


    uvicorn.run(

        "src.main:app",

        host="0.0.0.0",

        port=8000,

        reload=settings.DEBUG

    )