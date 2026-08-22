import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and configuration."""

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "QStock"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    # Keep the URL configurable through the environment so credentials are
    # never committed to source control.
    DATABASE_URL: str = "postgresql://qr_user@localhost:5432/qr_inventory"

    # Security - no production secret is stored in source control.
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://192.168.2.31:5173",
        "https://192.168.2.31:5173",
        "http://192.168.2.31:3000",
        "https://192.168.2.31:3000",
    ]

    # QR Code Settings
    QR_CODE_SIZE: int = 10
    QR_CODE_BORDER: int = 4
    QR_CODE_BOX_SIZE: int = 10

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 5242880

    # Email (Optional)
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False

    # Initial admin setup - credentials must come from the environment.
    INITIAL_ADMIN_EMAIL: str = ""
    INITIAL_ADMIN_PASSWORD: str = ""
    INITIAL_ADMIN_NAME: str = "System Administrator"
    INITIAL_ADMIN_PHONE: str = ""

    # -------------------------------------------------------------------------
    # AI Assistant
    # -------------------------------------------------------------------------
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Option B: Ollama (local)
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"

    # AI Assistant tuning
    AI_MAX_HISTORY_TURNS: int = 3
    AI_ANSWER_MAX_TOKENS: int = 120
    AI_ANSWER_NUM_CTX: int = 4096
    AI_CONTEXT_ROW_LIMIT: int = 15

    # Optional separate answer model. Empty means use the main model.
    OLLAMA_ANSWER_MODEL: str = ""
    OPENAI_ANSWER_MODEL: str = ""

    # Optional Ollama GPU layer override.
    OLLAMA_NUM_GPU: int | None = None

    # Ollama HTTP timeouts.
    OLLAMA_CONNECT_TIMEOUT: float = 30.0
    OLLAMA_READ_TIMEOUT: float = 300.0
    OLLAMA_WRITE_TIMEOUT: float = 30.0
    OLLAMA_POOL_TIMEOUT: float = 30.0

    # SQL-generation tuning.
    AI_SQL_MAX_TOKENS: int = 300
    AI_SQL_NUM_CTX: int = 4096

    # Disable internal model reasoning for fast, deterministic SQL/answers.
    OLLAMA_THINK: bool = False

    # Format simple list/data responses directly in Python to avoid an
    # unnecessary LLM call and reduce latency/cost.
    AI_DETERMINISTIC_LIST_ANSWERS: bool = True

    # -------------------------------------------------------------------------
    # AI performance instrumentation
    # -------------------------------------------------------------------------
    # Bounded in-process metrics are intentionally lightweight. They contain
    # aggregate timings/counters only, never prompts, SQL, user IDs, or PII.
    AI_METRICS_MAX_SAMPLES: int = 1000
    AI_PERFORMANCE_LOGGING: bool = True


settings = Settings()

# Ensure upload directory exists.
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)