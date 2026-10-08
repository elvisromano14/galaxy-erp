"""Modelos para sincronización offline y dispositivos móviles de campo."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class DispositivoSync(Base):
    """Dispositivo móvil o terminal autorizado para sincronización offline."""

    __tablename__ = "sync_dispositivo"

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
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    identificador_unico: Mapped[str] = mapped_column(String(120), nullable=False)
    ultimo_token: Mapped[int] = mapped_column(BigInteger, default=0)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "identificador_unico", name="uq_sync_dispositivo_identificador"
        ),
    )


class SyncOperacionLog(Base):
    """Registro de idempotencia y auditoría de operaciones enviadas offline."""

    __tablename__ = "sync_operacion_log"

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
    dispositivo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sync_dispositivo.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_op_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # PEDIDO_VENTA, COBRO_CLIENTE
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # APLICADA, RECHAZADA, DUPLICADA
    documento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    numero_documento: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("company_id", "client_op_id", name="uq_sync_operacion_client_op_id"),
    )


class SyncBloqueCorrelativo(Base):
    """Reserva de bloque de correlativos numéricos para emisión fuera de línea."""

    __tablename__ = "sync_bloque_correlativo"

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
    dispositivo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sync_dispositivo.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_documento: Mapped[str] = mapped_column(String(30), nullable=False)
    serie: Mapped[str] = mapped_column(String(10), default="")
    desde_numero: Mapped[int] = mapped_column(BigInteger, nullable=False)
    hasta_numero: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ultimo_usado: Mapped[int] = mapped_column(BigInteger, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
