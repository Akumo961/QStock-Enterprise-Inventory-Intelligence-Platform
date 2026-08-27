from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Verify database connectivity.

    Schema creation and upgrades are owned by Alembic. Keeping DDL out of
    application startup prevents an application process from silently
    mutating production schema.
    """
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
