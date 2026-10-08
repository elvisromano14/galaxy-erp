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

    # Seguridad y JWT
    JWT_SECRET_KEY: str = Field(
        default="change-this-in-production-secret-key-32b",
        description="Clave secreta para firma de JWT",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Zona horaria
    TIMEZONE: str = "America/Caracas"


settings = Settings()
