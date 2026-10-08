import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    slug: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    db_host: Mapped[str] = mapped_column(String(120), nullable=False, default="127.0.0.1")
    db_port: Mapped[int] = mapped_column(Integer, nullable=False, default=6432)
    db_name: Mapped[str] = mapped_column(String(63), unique=True, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="aprovisionando",
    )
    plan: Mapped[str] = mapped_column(String(40), nullable=False)
    es_canario: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    schema_rev: Mapped[str | None] = mapped_column(String(64), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "slug ~ '^[a-z][a-z0-9-]{1,38}[a-z0-9]$'",
            name="chk_tenant_slug_formato",
        ),
        CheckConstraint(
            "estado IN ('aprovisionando', 'activo', 'suspendido', 'archivado', 'fallido')",
            name="chk_tenant_estado_valido",
        ),
    )

    modulos: Mapped[list["TenantModulo"]] = relationship(
        "TenantModulo",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    jobs: Mapped[list["TenantJob"]] = relationship(
        "TenantJob",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def url_app(self, usuario: str = "erp_app", password: str = "") -> str:
        """Genera la URL de conexión a la base del cliente vía PgBouncer."""
        cred = f"{usuario}:{password}@" if password else f"{usuario}@"
        return f"postgresql+asyncpg://{cred}{self.db_host}:{self.db_port}/{self.db_name}"

    def url_owner(self, usuario: str = "erp_owner", password: str = "", puerto: int = 5432) -> str:
        """Genera la URL de conexión directa para migraciones y mantenimiento."""
        cred = f"{usuario}:{password}@" if password else f"{usuario}@"
        return f"postgresql+asyncpg://{cred}{self.db_host}:{puerto}/{self.db_name}"


class TenantModulo(Base):
    __tablename__ = "tenant_modulo"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        primary_key=True,
    )
    modulo: Mapped[str] = mapped_column(String(40), primary_key=True)
    habilitado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    vence_en: Mapped[date | None] = mapped_column(Date, nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="modulos")


class TenantJob(Base):
    __tablename__ = "tenant_job"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="SET NULL"),
        nullable=True,
    )
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="EN_CURSO")
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    iniciado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    terminado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", back_populates="jobs")


class PlataformaAdmin(Base):
    __tablename__ = "plataforma_admin"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
