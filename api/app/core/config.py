from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Galaxy ERP"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Base de datos de control (erp_control)
    CONTROL_DB_URL: str = Field(
        default="postgresql+asyncpg://erp_app:erp_app_pass@127.0.0.1:6432/erp_control",
        description="URL de conexión para plano de control (vía PgBouncer)",
    )
    CONTROL_DB_OWNER_URL: str = Field(
        default="postgresql+asyncpg://erp_owner:erp_owner_pass@127.0.0.1:5432/erp_control",
        description="URL directa para migraciones y operaciones DDL de control",
    )

    # Redis (caché, colas y locks)
    REDIS_URL: str = Field(
        default="redis://127.0.0.1:6379/0",
        description="URL de conexión a Redis",
    )

    # Seguridad, CORS y Hardening
    JWT_SECRET_KEY: str = Field(
        default="change-this-in-production-secret-key-32b",
        description="Clave secreta para firma de JWT",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: list[str] = Field(
        default=["*"],
        description="Lista de orígenes permitidos para CORS",
    )
    MAX_BODY_SIZE_MB: int = Field(
        default=10,
        description="Tamaño máximo permitido para payloads HTTP en MB",
    )
    RATE_LIMIT_LOGIN_MAX: int = Field(
        default=10,
        description="Máximo de peticiones de login permitidas por IP en la ventana de tiempo",
    )
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = Field(
        default=60,
        description="Ventana de tiempo para rate-limiting de login en segundos",
    )
    ENABLE_SECURITY_HEADERS: bool = True

    # Zona horaria
    TIMEZONE: str = "America/Caracas"


settings = Settings()
