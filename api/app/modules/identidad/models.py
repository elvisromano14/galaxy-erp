import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
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


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(200), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    roles: Mapped[list["Rol"]] = relationship(
        "Rol",
        secondary="usuario_rol",
        back_populates="usuarios",
        lazy="selectin",
    )


class Rol(Base):
    __tablename__ = "rol"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    es_sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    permisos: Mapped[list["Permiso"]] = relationship(
        "Permiso",
        secondary="rol_permiso",
        back_populates="roles",
        lazy="selectin",
    )
    usuarios: Mapped[list["Usuario"]] = relationship(
        "Usuario",
        secondary="usuario_rol",
        back_populates="roles",
    )


class Permiso(Base):
    __tablename__ = "permiso"

    codigo: Mapped[str] = mapped_column(String(60), primary_key=True)
    modulo: Mapped[str] = mapped_column(String(40), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)

    roles: Mapped[list["Rol"]] = relationship(
        "Rol",
        secondary="rol_permiso",
        back_populates="permisos",
    )


class RolPermiso(Base):
    __tablename__ = "rol_permiso"

    rol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rol.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permiso_codigo: Mapped[str] = mapped_column(
        String(60),
        ForeignKey("permiso.codigo", ondelete="CASCADE"),
        primary_key=True,
    )


class UsuarioRol(Base):
    __tablename__ = "usuario_rol"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        primary_key=True,
    )
    rol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rol.id", ondelete="CASCADE"),
        primary_key=True,
    )


class SesionRefresh(Base):
    __tablename__ = "sesion_refresh"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AuditLog(Base):
    """Registro de auditoría append-only por cliente."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    entidad: Mapped[str] = mapped_column(String(50), nullable=False)
    entidad_id: Mapped[str] = mapped_column(String(100), nullable=False)
    accion: Mapped[str] = mapped_column(String(30), nullable=False)
    datos_previos: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    datos_nuevos: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
